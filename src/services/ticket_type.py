from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core import logger
from src.core.exception import TicketTypeDeleteError, TicketTypeNotFoundError
from src.models import TicketType
from src.schemas.ticket_type import TicketTypeCreate, TicketTypeUpdate


class TicketTypeService:
    def __init__(self, session: AsyncSession) -> None:
        self.db = session

    async def create(self, ticket_type_data: TicketTypeCreate) -> TicketType:
        new_ticket_type = TicketType(**ticket_type_data.model_dump())
        self.db.add(new_ticket_type)

        try:
            await self.db.commit()
            await self.db.refresh(new_ticket_type)

            logger.info(f"TicketType created: {new_ticket_type.id}")
        except SQLAlchemyError:
            await self.db.rollback()
            raise

        return new_ticket_type

    async def get(self, ticket_type_id: int) -> TicketType:
        ticket_type = await self.db.get(TicketType, ticket_type_id)
        if not ticket_type:
            raise TicketTypeNotFoundError("Ticket type not found")
        return ticket_type

    async def get_all_for_event(
        self, event_id: int, offset: int, limit: int
    ) -> Sequence[TicketType]:
        query = (
            select(TicketType)
            .where(TicketType.event_id == event_id)
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.scalars(query)

        return result.all()

    async def delete(self, ticket_type_id: int) -> None:
        ticket_type = await self.get(ticket_type_id)

        try:
            await self.db.delete(ticket_type)
            await self.db.commit()

            logger.info(f"Ticket type deleted: {ticket_type_id}")
        except IntegrityError as e:
            await self.db.rollback()
            logger.warning(
                f"Attempt to delete ticket type {ticket_type_id} with existing tickets"
            )
            raise TicketTypeDeleteError(
                "Cannot delete ticket type with existing tickets"
            ) from e

    async def update(
        self, ticket_type_id: int, update_data: TicketTypeUpdate
    ) -> TicketType:
        ticket_type = await self.get(ticket_type_id)

        update_dict = update_data.model_dump(exclude_unset=True)
        if not update_dict:
            return ticket_type

        for key, value in update_dict.items():
            setattr(ticket_type, key, value)

        try:
            await self.db.commit()
            await self.db.refresh(ticket_type)

            logger.info(f"Ticket type updated: {ticket_type_id}")
        except SQLAlchemyError:
            await self.db.rollback()
            raise

        return ticket_type
