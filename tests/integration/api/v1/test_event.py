import pytest
from datetime import datetime

@pytest.mark.asyncio
async def test_create_event(client):
    event_payload = {
        'title' : 'test event',
        'date' : datetime.now().isoformat(),
        'tickets_quantity' : 100,
        'country' : 'Poland',
        'city' : 'Wroclaw',
        'street_address' : 'test street 1'
    }
    response = await client.post('/api/v1/events/', json=event_payload)
    assert response.status_code == 201

@pytest.mark.asyncio
async def test_delete_event_with_ticket(client):
    event_payload = {
        'title': 'test event',
        'date': datetime.now().isoformat(),
        'tickets_quantity': 100,
        'country': 'Poland',
        'city': 'Wroclaw',
        'street_address': 'test street 1'
    }
    event = await client.post('/api/v1/events/', json=event_payload)
    assert event.status_code == 201
    event_id = event.json().get('id')

    ticket_payload = {
        'event_id' : event_id,
        'price' : 50
    }
    ticket = await client.post('/api/v1/tickets/', json=ticket_payload)
    assert ticket.status_code == 201

    response = await client.delete(f'/api/v1/events/{event_id}')

    assert response.status_code == 409