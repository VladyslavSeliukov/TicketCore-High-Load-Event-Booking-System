import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.ticket import Ticket
from tests.factories import EventFactory


async def test_params_of_event(db_connection: AsyncSession) -> None:
    event = EventFactory.build()
    db_connection.add(event)
    await db_connection.commit()
    await db_connection.refresh(event)

    bad_ticket = Ticket(event_id=event.id, price=-100)
    db_connection.add(bad_ticket)

    with pytest.raises(IntegrityError):
        await db_connection.commit()
