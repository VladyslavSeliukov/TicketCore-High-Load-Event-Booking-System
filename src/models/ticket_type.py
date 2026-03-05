from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base

if TYPE_CHECKING:
    from src.models.event import Event
    from src.models.ticket import Ticket


class TicketType(Base):
    __tablename__ = "ticket_types"

    id: Mapped[int] = mapped_column(primary_key=True)

    name: Mapped[str] = mapped_column(String(50), nullable=False)
    price: Mapped[int] = mapped_column(Integer, nullable=False)

    tickets_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    tickets_sold: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # 1:N
    tickets: Mapped[list["Ticket"]] = relationship(
        "Ticket", back_populates="ticket_type"
    )

    event_id: Mapped[int] = mapped_column(
        ForeignKey("events.id", ondelete="RESTRICT"), nullable=False
    )
    # N:1
    event: Mapped["Event"] = relationship("Event", back_populates="ticket_types")

    __table_args__ = (
        CheckConstraint(sqltext="price >= 0", name="check_ticket_price"),
        CheckConstraint(sqltext="tickets_quantity > 0", name="check_ticket_quantity"),
        CheckConstraint(sqltext="tickets_sold >= 0", name="check_ticket_sold"),
        CheckConstraint(
            sqltext="tickets_quantity >= tickets_sold", name="check_sold_limit"
        ),
    )
