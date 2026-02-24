from polyfactory import Use
from polyfactory.factories.pydantic_factory import ModelFactory
from polyfactory.factories.sqlalchemy_factory import SQLAlchemyFactory

from src.core.security import get_password_hash
from src.models import Event, Ticket, User
from src.schemas import EventCreate


class UserFactory(SQLAlchemyFactory[User]):
    __model__ = User

    hashed_password = get_password_hash('very_secure_password')
    is_superuser = False
    is_active = True

    tickets = Use(list)

    @classmethod
    def email(cls) -> str:
        return cls.__faker__.email()

class EventFactory(SQLAlchemyFactory[Event]):
    __model__ = Event

    tickets_sold = 0
    tickets_quantity = 100

    tickets = Use(list)

class TicketFactory(SQLAlchemyFactory[Ticket]):
    __model__ = Ticket

    owner = Use(UserFactory.build)
    event = Use(EventFactory.build)

class EventPayloadFactory(ModelFactory[EventCreate]):
    __model__ = EventCreate