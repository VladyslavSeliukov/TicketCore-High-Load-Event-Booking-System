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
    """Service for managing event lifecycle.

    Handles creation, retrieval, updates, and deletion.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.db = session

    async def create(self, event_data: EventCreate) -> Event:
        """Create a new event and persist it to the database.

        Args:
            event_data: Schema containing event details like title, date, and location.

        Returns:
            The newly created Event instance.

        Raises:
            SQLAlchemyError: If the database transaction fails.
        """
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
        """Retrieve a specific event by its ID along with its associated ticket types.

        Args:
            event_id: The unique identifier of the event.

        Returns:
            The requested Event instance.

        Raises:
            EventNotFoundError: If no event with the given ID exists.
        """
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
        """Retrieve a paginated list of events.

        Args:
            offset: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            A sequence of Event instances.
        """
        query = (
            select(Event)
            .options(selectinload(Event.ticket_types))
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.scalars(query)
        return result.all()

    async def delete(self, event_id: int) -> None:
        """Remove an event from the database.

        Prevents deletion if there are already tickets associated with this event
        to maintain data integrity.

        Args:
            event_id: The unique identifier of the event to delete.

        Raises:
            EventNotFoundError: If the event does not exist.
            EventDeleteError: If the event cannot be deleted due to existing tickets.
            SQLAlchemyError: If the database transaction fails.
        """
        event = await self.db.get(Event, event_id)

        if not event:
            raise EventNotFoundError("Event not found")

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
        """Update specific fields of an existing event.

        Ignores unset fields in the update payload, applying only the provided changes.

        Args:
            event_id: The unique identifier of the event to update.
            update_data: Schema containing the fields to be updated.

        Returns:
            The updated Event instance.

        Raises:
            EventNotFoundError: If the event does not exist.
            SQLAlchemyError: If the database transaction fails.
        """
        event = await self.db.get(Event, event_id)

        if not event:
            raise EventNotFoundError("Event not found")

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
