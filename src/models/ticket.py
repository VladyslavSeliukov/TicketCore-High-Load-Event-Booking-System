import enum
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.models.ticket_type import TicketType
    from src.models.user import User


class TicketStatus(enum.Enum):
    """Defines the lifecycle states of a ticket reservation.

    - RESERVED: Ticket is temporarily locked for a user, awaiting payment.
    - SOLD: Payment is successfully processed, and the ticket is permanently assigned.
    - CANCELED: Reservation timed out or was manually aborted;
    inventory is released back to the event.
    """

    RESERVED = "RESERVED"
    SOLD = "SOLD"
    CANCELED = "CANCELED"


class Ticket(Base, TimestampMixin):
    """Represents an individual ticket assigned to a user.

    Tracks the lifecycle of a ticket reservation through its status
    (RESERVED, SOLD, CANCELED) and links a specific user to a ticket type.
    """

    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(primary_key=True)

    ticket_type_id: Mapped[int] = mapped_column(
        ForeignKey("ticket_types.id", ondelete="RESTRICT"), nullable=False
    )
    # N:1
    ticket_type: Mapped["TicketType"] = relationship(
        "TicketType", back_populates="tickets"
    )

    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    owner: Mapped["User"] = relationship("User", back_populates="tickets")

    status: Mapped[TicketStatus] = mapped_column(
        default=TicketStatus.RESERVED, nullable=False, index=True
    )

    @property
    def event_title(self) -> str:
        """Retrieve the title of the associated event.

        Safely traverses the relationship graph (Ticket -> TicketType -> Event)
        to get the title. Returns 'Unknown' if the relations are not eagerly loaded.
        """
        if self.ticket_type is not None and self.ticket_type.event is not None:
            return self.ticket_type.event.title
        return "Unknown"
