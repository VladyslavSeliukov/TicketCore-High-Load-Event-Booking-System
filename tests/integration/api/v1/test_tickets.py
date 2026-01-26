import pytest
from datetime import datetime

@pytest.mark.asyncio
async def test_create_event_flow(client):
    event_payload = {
        'title' : 'test event',
        'date' : datetime.now().isoformat(),
        'tickets_quantity' : 50,
        'country' : 'Poland',
        'city' : 'Wroclaw',
        'street_address' : 'test street 1'
    }
    response = await client.post('/api/v1/events/', json=event_payload)
    assert response.status_code == 201
    event_id = response.json().get('id')

    ticket_payload = {
        'event_id' : event_id,
        'price' : 500
    }
    response = await client.post('/api/v1/tickets/', json=ticket_payload)
    assert response.status_code == 201
    assert response.json()['event_title'] == 'test event'

@pytest.mark.asyncio
async def test_get_unexisted_ticket(client):
    response = await client.get('/api/v1/tickets/9999')
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_post_ticket_with_unexisted_event(client):
    ticket_payload = {
        'event_id' : '0',
        'price' : 50
    }
    response = await client.post('/api/v1/tickets/', json=ticket_payload)
    assert response.status_code == 404