import pytest
from datetime import datetime

from factories import EventFactory, TicketFactory
from src.models import Ticket

@pytest.mark.asyncio
async def test_create_event(client):
    event = EventFactory.build()

    event_payload = {
        'title' : event.title,
        'date' : event.date.isoformat(),
        'tickets_quantity' : event.tickets_quantity,
        'country' : event.country,
        'city' : event.city,
        'street_address' : event.street_address
    }
    response = await client.post('/api/v1/events/', json=event_payload)
    assert response.status_code == 201

@pytest.mark.asyncio
async def test_delete_event_with_ticket(client, db_connection):
    event = EventFactory.build()
    db_connection.add(event)
    await db_connection.commit()
    await db_connection.refresh(event)

    ticket = Ticket(event_id = event.id, price = 50)
    db_connection.add(ticket)
    await db_connection.commit()

    response = await client.delete(f'/api/v1/events/{event.id}')
    assert response.status_code == 409