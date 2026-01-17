from sqlalchemy import Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.db.base import Base

class Ticket(Base):
    __tablename__ = 'tickets'

    id: Mapped[int] = mapped_column(primary_key=True)

    event_id: Mapped[int] = mapped_column(ForeignKey('events.id'), nullable=False)

    price: Mapped[int] = mapped_column(Integer, nullable=False)

    event: Mapped['Event'] = relationship('Event', back_populates='tickets')