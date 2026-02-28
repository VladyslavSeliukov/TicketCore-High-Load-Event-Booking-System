from collections.abc import Sequence

from sqlalchemy import select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core import logger
from src.core.exception import (
    EventNotFoundError,
    TicketNotFoundError,
    TicketsSoldOutError,
)
from src.models import Event, Ticket
from src.schemas import TicketCreate


class TicketService:
    def __init__(self, session: AsyncSession):
        self.db = session

    async def create(self, user_id: int, ticket_data: TicketCreate) -> Ticket:
        query = (
            update(Event)
            .where(Event.id == ticket_data.event_id)
            .where(Event.tickets_quantity > Event.tickets_sold)
            .values(tickets_sold=Event.tickets_sold + 1)
            .returning(Event)
        )
        event = await self.db.scalar(query)

        if not event:
            check_query = select(Event.id).where(Event.id == ticket_data.event_id)
            if not await self.db.scalar(check_query):
                raise EventNotFoundError("Event not found")
            raise TicketsSoldOutError("Sold out. No ticket available")

        new_ticket = Ticket(owner_id=user_id, **ticket_data.model_dump())
        self.db.add(new_ticket)
        try:
            await self.db.commit()
            await self.db.refresh(new_ticket)
            new_ticket.event = event

            logger.info(f"Ticket created {new_ticket.id}")
        except SQLAlchemyError:
            await self.db.rollback()
            raise

        return new_ticket

    async def get(self, owner_id: int, ticket_id: int) -> Ticket:
        query = (
            select(Ticket)
            .options(selectinload(Ticket.event))
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
            .options(selectinload(Ticket.event))
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
                update(Event)
                .where(Event.id == ticket.event_id)
                .values(tickets_sold=Event.tickets_sold - 1)
            )
            await self.db.execute(update_query)

            await self.db.delete(ticket)
            await self.db.commit()

            logger.info(f"Ticket deleted: {ticket_id}")
        except SQLAlchemyError:
            await self.db.rollback()
            raise
