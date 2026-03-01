from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base

if TYPE_CHECKING:
    from src.models.ticket_type import TicketType
    from src.models.user import User


class Ticket(Base):
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

    @property
    def event_title(self) -> str:
        if self.ticket_type is not None and self.ticket_type.event is not None:
            return self.ticket_type.event.title
        return "Unknown"
