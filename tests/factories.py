from polyfactory import Use
from polyfactory.factories.sqlalchemy_factory import SQLAlchemyFactory

from src.core.security import get_password_hash
from src.models import Event, Ticket, User

class UserFactory(SQLAlchemyFactory[User]):
    __model__ = User

    hashed_password = get_password_hash('very_secure_password')
    is_active = True
    is_superuser = False

class EventFactory(SQLAlchemyFactory[Event]):
    __model__ = Event

    tickets = Use(list)

class TicketFactory(SQLAlchemyFactory[Ticket]):
    __model__ = Ticket

    owner = Use(UserFactory)