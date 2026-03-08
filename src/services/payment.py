from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core import logger
from src.core.exception import (
    TicketAlreadyPaidError,
    TicketNotFoundError,
    TicketReservationExpireError,
)
from src.models import Ticket
from src.models.ticket import TicketStatus


class PaymentService:
    """Service for processing ticket payments and managing state transitions."""

    def __init__(self, session: AsyncSession) -> None:
        self.db = session

    async def pay_for_ticket(self, ticket_id: int, owner_id: int) -> Ticket:
        """Process payment for a reserved ticket and mark it as sold.

        Uses a database lock (`with_for_update`) to prevent race conditions
        during concurrent payment attempts.

        Args:
            ticket_id: The ID of the ticket to pay for.
            owner_id: The ID of the user who owns the ticket.

        Returns:
            The updated Ticket instance with 'SOLD' status.

        Raises:
            TicketNotFoundError: If the ticket does not exist
            or belongs to another user.
            TicketAlreadyPaidError: If the ticket is already in 'SOLD' status.
            TicketReservationExpireError: If the ticket reservation was 'CANCELED'.
            SQLAlchemyError: If the database transaction fails.
        """
        ticket_query = (
            select(Ticket)
            .where(Ticket.id == ticket_id)
            .where(Ticket.owner_id == owner_id)
            .with_for_update()
        )
        ticket = await self.db.scalar(ticket_query)

        if not ticket:
            raise TicketNotFoundError("Ticket not found")

        if ticket.status == TicketStatus.SOLD:
            logger.warning(f"Attempt to pay for already SOLD ticket: {ticket_id}")
            raise TicketAlreadyPaidError("This ticket is already paid")

        if ticket.status == TicketStatus.CANCELED:
            logger.warning(f"Attempt to pay for CANCELED ticket: {ticket_id}")
            raise TicketReservationExpireError("Reservation time expired")

        ticket.status = TicketStatus.SOLD

        try:
            await self.db.commit()
            await self.db.refresh(ticket)

            logger.info(f"Ticket {ticket_id} successfully PAID")
        except SQLAlchemyError:
            await self.db.rollback()
            raise

        return ticket
