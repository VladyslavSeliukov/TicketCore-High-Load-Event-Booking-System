from datetime import UTC, datetime

from polyfactory import Use
from polyfactory.factories.pydantic_factory import ModelFactory
from polyfactory.factories.sqlalchemy_factory import SQLAlchemyFactory

from src.core.security import get_password_hash
from src.models import Event, Ticket, TicketType, User
from src.models.ticket import TicketStatus
from src.schemas import EventCreate, TicketCreate, UserCreate
from src.schemas.ticket_type import TicketTypeCreate


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

    @classmethod
    def date(cls) -> datetime:
        return cls.__faker__.date_time(tzinfo=UTC)

    @classmethod
    def title(cls) -> str:
        return cls.__faker__.catch_phrase()

    @classmethod
    def country(cls) -> str:
        return cls.__faker__.country()

    @classmethod
    def city(cls) -> str:
        return cls.__faker__.city()

    @classmethod
    def street_address(cls) -> str:
        return cls.__faker__.street_address()

    @classmethod
    def tickets(cls) -> list[Ticket]:
        return []

    @classmethod
    def ticket_types(cls) -> list[TicketType]:
        return []


class TicketTypeFactory(SQLAlchemyFactory[TicketType]):
    __model__ = TicketType

    @classmethod
    def name(cls) -> str:
        return cls.__faker__.word()

    @classmethod
    def tickets_quantity(cls) -> int:
        return cls.__faker__.random_int(min=50, max=500)

    @classmethod
    def tickets_sold(cls) -> int:
        return cls.__faker__.random_int(min=0, max=49)

    @classmethod
    def price(cls) -> int:
        return cls.__faker__.random_int(min=10, max=500)

    @classmethod
    def tickets(cls) -> list[Ticket]:
        return []

    event = Use(EventFactory.build)


class TicketFactory(SQLAlchemyFactory[Ticket]):
    __model__ = Ticket

    owner = Use(UserFactory.build)
    ticket_type = Use(TicketTypeFactory.build)
    status = TicketStatus.RESERVED


class EventPayloadFactory(ModelFactory[EventCreate]):
    __model__ = EventCreate


class TicketTypePayloadFactory(ModelFactory[TicketTypeCreate]):
    __model__ = TicketTypeCreate


class TicketPayloadFactory(ModelFactory[TicketCreate]):
    __model__ = TicketCreate


class UserPayloadFactory(ModelFactory[UserCreate]):
    __model__ = UserCreate
