from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core import logger
from src.core.exception import EventDeleteError, EventNotFoundError
from src.models import Event
from src.schemas import EventCreate, EventUpdate


class EventService:
    def __init__(self, session: AsyncSession) -> None:
        self.db = session

    async def create(self, event_data: EventCreate) -> Event:
        new_event = Event(**event_data.model_dump())
        self.db.add(new_event)
        try:
            await self.db.commit()
            await self.db.refresh(new_event)

            logger.info(f"Event created {new_event.id}")
        except SQLAlchemyError:
            await self.db.rollback()
            raise

        return new_event

    async def get(self, event_id: int) -> Event:
        query = (
            select(Event)
            .options(selectinload(Event.ticket_types))
            .where(Event.id == event_id)
        )
        event = await self.db.scalar(query)
        if not event:
            raise EventNotFoundError("Event not found")
        return event

    async def get_all(self, offset: int, limit: int) -> Sequence[Event]:
        query = (
            select(Event)
            .options(selectinload(Event.ticket_types))
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.scalars(query)
        return result.all()

    async def delete(self, event_id: int) -> None:
        event = await self.get(event_id)

        try:
            await self.db.delete(event)
            await self.db.commit()

            logger.info(f"Event deleted: {event_id}")
        except IntegrityError as e:
            await self.db.rollback()

            logger.warning(
                f"Attempt to delete event {event_id} failed: tickets already exist"
            )
            raise EventDeleteError("Cannot delete event with existing tickets") from e
        except SQLAlchemyError:
            await self.db.rollback()
            raise

    async def update(self, event_id: int, update_data: EventUpdate) -> Event:
        event = await self.get(event_id)

        update_dict = update_data.model_dump(exclude_unset=True)
        if not update_dict:
            return event

        for key, value in update_dict.items():
            setattr(event, key, value)

        try:
            await self.db.commit()
            await self.db.refresh(event)

            logger.info(f"Event updated: {event_id}")
        except SQLAlchemyError:
            await self.db.rollback()
            raise

        return event
