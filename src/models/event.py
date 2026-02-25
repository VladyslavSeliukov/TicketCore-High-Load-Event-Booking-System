from sqlalchemy import String, Integer, DateTime, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.db.base import Base
from datetime import datetime


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True)

    title: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    date: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    country: Mapped[str] = mapped_column(String(100), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    street_address: Mapped[str] = mapped_column(String(100), nullable=False)

    tickets: Mapped[list["Ticket"]] = relationship("Ticket", back_populates="event")
    tickets_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    tickets_sold: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    __table_args__ = (
        CheckConstraint("tickets_quantity > 0", name="check_ticket_quantity"),
        CheckConstraint("tickets_sold <= tickets_quantity", name="check_sold_limit"),
    )
