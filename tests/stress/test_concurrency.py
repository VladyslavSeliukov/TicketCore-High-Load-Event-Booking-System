import pytest
import asyncio
from datetime import datetime

@pytest.mark.asyncio
async def test_race_condition_overselling(client):
    event_payload = {
        'title': 'test event',
        'date': datetime.now().isoformat(),
        'tickets_quantity': 5,
        'country': 'Poland',
        'city': 'Wroclaw',
        'street_address': 'test street 1'
    }
    event_response = await client.post('/api/v1/events/', json=event_payload)
    assert event_response.status_code == 201
    event_id = event_response.json()['id']

    ticket_payload = {
        'event_id' : event_id,
        'price' : 100
    }
    async def buy_ticket():
        return await client.post('/api/v1/tickets/', json=ticket_payload)
    buy_ticket_task = [buy_ticket() for _ in range(20)]
    buy_ticket_response = await asyncio.gather(*buy_ticket_task)

    success_count = sum(1 for r in buy_ticket_response if r.status_code == 201)
    conflict_count = sum(1 for r in buy_ticket_response if r.status_code == 409)

    assert success_count == 5
    assert conflict_count == 15