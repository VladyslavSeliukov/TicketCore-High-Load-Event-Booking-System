from datetime import datetime

import pytest
from sqlalchemy.exc import IntegrityError

from src.models import Event
from src.models.ticket import Ticket


async def test_params_of_event(db_connection):
    event = Event(
       title='test event',
        date=datetime.now(),
        tickets_quantity=50,
        country='Poland',
        city='Wroclaw',
        street_address='test street 1'
    )
    db_connection.add(event)
    await db_connection.commit()
    await db_connection.refresh(event)

    bad_ticket = Ticket(
        event_id = event.id,
        price = -100
    )
    db_connection.add(bad_ticket)

    with pytest.raises(IntegrityError):
        await db_connection.commit()