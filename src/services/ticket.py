from collections.abc import Sequence

from sqlalchemy import exists, select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core import logger
from src.core.exception import (
    TicketNotFoundError,
    TicketsSoldOutError,
    TicketTypeNotFoundError,
)
from src.models import Ticket, TicketType
from src.schemas import TicketCreate


class TicketService:
    def __init__(self, session: AsyncSession) -> None:
        self.db = session

    async def create(self, user_id: int, ticket_data: TicketCreate) -> Ticket:
        ticket_type_query = (
            update(TicketType)
            .where(TicketType.id == ticket_data.ticket_type_id)
            .where(TicketType.tickets_quantity > TicketType.tickets_sold)
            .values(tickets_sold=TicketType.tickets_sold + 1)
            .returning(TicketType)
        )
        ticket_type = await self.db.scalar(ticket_type_query)

        if not ticket_type:
            check_query = select(
                exists().where(TicketType.id == ticket_data.ticket_type_id)
            )
            if not await self.db.scalar(check_query):
                raise TicketTypeNotFoundError("Ticket type not found")
            raise TicketsSoldOutError("Sold out. No tickets of this type available")

        new_ticket = Ticket(owner_id=user_id, **ticket_data.model_dump())
        self.db.add(new_ticket)
        try:
            await self.db.commit()

            query_load = (
                select(Ticket)
                .options(selectinload(Ticket.ticket_type).joinedload(TicketType.event))
                .where(Ticket.id == new_ticket.id)
            )

            loaded_ticket = await self.db.scalar(query_load)

            if not loaded_ticket:
                raise SQLAlchemyError("Failed to load ticket after creation")

            logger.info(f"Ticket created: {loaded_ticket.id}")
        except SQLAlchemyError:
            await self.db.rollback()
            raise
        return loaded_ticket

    async def get(self, owner_id: int, ticket_id: int) -> Ticket:
        query = (
            select(Ticket)
            .options(selectinload(Ticket.ticket_type).joinedload(TicketType.event))
            .where(Ticket.id == ticket_id)
            .where(Ticket.owner_id == owner_id)
        )
        ticket = await self.db.scalar(query)
        if not ticket:
            raise TicketNotFoundError("Ticket not found")

        return ticket

    async def get_all_for_user(
        self, owner_id: int, offset: int, limit: int
    ) -> Sequence[Ticket]:
        query = (
            select(Ticket)
            .options(selectinload(Ticket.ticket_type).joinedload(TicketType.event))
            .where(Ticket.owner_id == owner_id)
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.scalars(query)
        return result.all()

    async def delete(self, owner_id: int, ticket_id: int) -> None:
        ticket = await self.get(owner_id=owner_id, ticket_id=ticket_id)

        try:
            update_query = (
                update(TicketType)
                .where(TicketType.id == ticket.ticket_type_id)
                .values(tickets_sold=TicketType.tickets_sold - 1)
            )
            await self.db.execute(update_query)

            await self.db.delete(ticket)
            await self.db.commit()

            logger.info(f"Ticket deleted: {ticket_id}")
        except SQLAlchemyError:
            await self.db.rollback()
            raise
