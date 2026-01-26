import pytest
from sqlalchemy.exc import IntegrityError
from datetime import datetime
from src.models.event import Event

@pytest.mark.asyncio
async def test_event_with_negative_quantity(db_connection):
    bad_event = Event(
        title = 'test event',
        date = datetime.now(),
        tickets_quantity = -50,
        country = 'Poland',
        city = 'Wroclaw',
        street_address = 'test street 1'
    )
    db_connection.add(bad_event)

    with pytest.raises(IntegrityError):
        await db_connection.commit()

    await db_connection.rollback()