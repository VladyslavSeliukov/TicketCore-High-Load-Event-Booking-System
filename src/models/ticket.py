from sqlalchemy import Integer, ForeignKey, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.db.base import Base

class Ticket(Base):
    __tablename__ = 'tickets'

    id: Mapped[int] = mapped_column(primary_key=True)

    price: Mapped[int] = mapped_column(Integer, nullable=False)

    event_id: Mapped[int] = mapped_column(ForeignKey('events.id', ondelete='RESTRICT'), nullable=False)
    event: Mapped['Event'] = relationship('Event', back_populates='tickets')

    owner_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='RESTRICT'), nullable=False)
    owner: Mapped['User'] = relationship('User', back_populates='tickets')

    __table_args__ = (
        CheckConstraint('price > 0', name='check_ticket_price'),
    )