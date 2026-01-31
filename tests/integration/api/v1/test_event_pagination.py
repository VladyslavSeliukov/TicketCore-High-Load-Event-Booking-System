import pytest

from conftest import db_connection
from factories import EventFactory
from src.models import Ticket

@pytest.mark.asyncio
async def test_event_pagination(client, db_connection):
    event_batch = [
        EventFactory.build(
            title=f'test event №{i}'
        ) for i in range(15)
    ]
    db_connection.add_all(event_batch)
    await db_connection.commit()

    response = await client.get('/api/v1/events/?page_limit=10&offset=0')
    assert response.status_code == 200

    data = response.json()
    assert len(data) == 10
    assert data[0]['title'] == 'test event №0'
    assert data[9]['title'] == 'test event №9'

@pytest.mark.asyncio
async def test_ticket_pagination(client,db_connection):
    event = EventFactory.build()
    db_connection.add(event)
    await db_connection.commit()
    await db_connection.refresh(event)

    ticket_batch = [
        Ticket(
            event_id = event.id,
            price = (i + 1) *10
        ) for i in range(15)
    ]
    db_connection.add_all(ticket_batch)
    await db_connection.commit()

    response = await client.get('/api/v1/tickets/?page_limit=10&offset=0')
    assert response.status_code == 200

    data = response.json()
    assert len(data) == 10
    assert data[0]['price'] == 10
    assert data[9]['price'] == 100