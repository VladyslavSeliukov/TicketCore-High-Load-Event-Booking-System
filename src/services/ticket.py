from collections.abc import Sequence

from arq import ArqRedis
from sqlalchemy import exists, select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core import logger, settings
from src.core.exception import (
    TicketNotFoundError,
    TicketsSoldOutError,
    TicketTypeNotFoundError,
)
from src.models import Ticket, TicketType
from src.schemas import TicketCreate


class TicketService:
    """Service for handling ticket reservations.

    Manages ticket retrievals and inventory state.
    """

    def __init__(self, session: AsyncSession, arq_pool: ArqRedis) -> None:
        self.db = session
        self.arq_pool = arq_pool

    async def create(self, user_id: int, ticket_data: TicketCreate) -> Ticket:
        """Reserve a ticket for a user and schedule an expiration task.

        Decrements the available ticket quantity for the specific ticket type.
        If the ticket is successfully created, enqueues a background job (ARQ)
        to release the reservation if it remains unpaid.

        Args:
            user_id: The ID of the user making the reservation.
            ticket_data: Schema containing the ticket type ID.

        Returns:
            The newly created Ticket instance.

        Raises:
            TicketTypeNotFoundError: If the requested ticket type does not exist.
            TicketsSoldOutError: If there are no available tickets left for this type.
            SQLAlchemyError: If the database transaction fails.
        """
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
            await self.db.refresh(new_ticket)

            logger.info(f"Ticket created: {new_ticket.id}")

            await self.arq_pool.enqueue_job(
                "release_unpaid_ticket",
                new_ticket.id,
                _defer_by=settings.TICKET_RESERVATION_TIME_SECONDS,
            )
        except SQLAlchemyError:
            await self.db.rollback()
            raise

        return new_ticket

    async def get(self, owner_id: int, ticket_id: int) -> Ticket:
        """Retrieve a specific ticket belonging to a user.

        Eagerly loads the associated ticket type and event details.

        Args:
            owner_id: The ID of the user who owns the ticket.
            ticket_id: The unique identifier of the ticket.

        Returns:
            The requested Ticket instance.

        Raises:
            TicketNotFoundError: If the ticket does not exist
            or does not belong to the user.
        """
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
        """Retrieve a paginated list of tickets owned by a specific user.

        Args:
            owner_id: The ID of the user.
            offset: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            A sequence of Ticket instances belonging to the user.
        """
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
        """Cancel a ticket reservation and restore inventory.

        Deletes the ticket record and increments the available quantity
        for the associated ticket type.

        Args:
            owner_id: The ID of the user attempting to delete the ticket.
            ticket_id: The unique identifier of the ticket.

        Raises:
            TicketNotFoundError: If the ticket does not exist
            or does not belong to the user.
            SQLAlchemyError: If the database transaction fails during restoration.
        """
        query = (
            select(Ticket)
            .where(Ticket.id == ticket_id)
            .where(Ticket.owner_id == owner_id)
        )
        ticket = await self.db.scalar(query)

        if not ticket:
            raise TicketNotFoundError("Ticket not found")
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
