from polyfactory import Use
from polyfactory.factories.sqlalchemy_factory import SQLAlchemyFactory
from src.models import Event, Ticket

class EventFactory(SQLAlchemyFactory[Event]):
    __model__ = Event
    tickets = Use(list)

class TicketFactory(SQLAlchemyFactory[Ticket]):
    __model__ = Ticket