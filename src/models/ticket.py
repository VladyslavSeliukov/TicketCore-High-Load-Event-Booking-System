from sqlalchemy import String, Integer, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column
from src.db.base import Base

class Ticket(Base):
    __tablename__ = 'tickets'

    id: Mapped[int] = mapped_column(primary_key=True)

    event_name: Mapped[int] = mapped_column(String(100), index=True)
    price: Mapped[int] = mapped_column(Integer)
    quantity: Mapped[int] = mapped_column(Integer)

    __table_args__ = (
        CheckConstraint("quantity >= 0", name='check_ticket_quantity'),
    )