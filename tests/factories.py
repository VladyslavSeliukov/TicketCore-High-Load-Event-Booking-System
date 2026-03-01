from polyfactory import Use
from polyfactory.factories.pydantic_factory import ModelFactory
from polyfactory.factories.sqlalchemy_factory import SQLAlchemyFactory

from src.core.security import get_password_hash
from src.models import Event, Ticket, User
from src.schemas import EventCreate


class UserFactory(SQLAlchemyFactory[User]):
    __model__ = User

    hashed_password: str = get_password_hash("very_secure_password")
    is_superuser = False
    is_active = True

    @classmethod
    def email(cls) -> str:
        return cls.__faker__.email()

    @classmethod
    def tickets(cls) -> list[Ticket]:
        return []


class EventFactory(SQLAlchemyFactory[Event]):
    __model__ = Event

    tickets_sold: int = 0
    tickets_quantity: int = 100

    @classmethod
    def title(cls) -> str:
        return cls.__faker__.catch_phrase()

    @classmethod
    def country(cls) -> str:
        return cls.__faker__.catch_phrase()

    @classmethod
    def city(cls) -> str:
        return cls.__faker__.catch_phrase()

    @classmethod
    def street_address(cls) -> str:
        return cls.__faker__.catch_phrase()

    @classmethod
    def tickets(cls) -> list[Ticket]:
        return []


class TicketFactory(SQLAlchemyFactory[Ticket]):
    __model__ = Ticket

    owner = Use(UserFactory.build)
    event = Use(EventFactory.build)


class EventPayloadFactory(ModelFactory[EventCreate]):
    __model__ = EventCreate
