import pytest
from sqlalchemy.exc import IntegrityError
from datetime import datetime

from factories import EventFactory
from src.models.event import Event

@pytest.mark.asyncio
async def test_event_with_negative_quantity(db_connection):
    bad_event = EventFactory.build(tickets_quantity = -50)
    db_connection.add(bad_event)

    with pytest.raises(IntegrityError):
        await db_connection.commit()

    await db_connection.rollback()