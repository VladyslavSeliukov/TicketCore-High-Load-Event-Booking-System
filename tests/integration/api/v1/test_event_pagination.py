import pytest
from datetime import datetime

@pytest.mark.asyncio
async def test_event_pagination(client):
    for i in range(15):
        response = await client.post('/api/v1/events/', json={
            'title': f'test event №{i}',
            'date': datetime.now().isoformat(),
            'tickets_quantity': 50,
            'country': 'Poland',
            'city': 'Wroclaw',
            'street_address': 'test street 1'
        })
        assert response.status_code == 201

    response = await client.get('/api/v1/events/?page_limit=10&offset=0')
    data = response.json()

    assert len(data) == 10
    for i in range(10):
        assert data[i]['title'] == f'test event №{i}'

@pytest.mark.asyncio
async def test_ticket_pagination(client):
    response = await client.post('/api/v1/events/', json={
        'title': f'test event №1',
        'date': datetime.now().isoformat(),
        'tickets_quantity': 50,
        'country': 'Poland',
        'city': 'Wroclaw',
        'street_address': 'test street 1'
    })
    assert response.status_code == 201
    event_id = response.json()['id']

    for i in range(15):
        response = await client.post('/api/v1/tickets/', json={
            'event_id' : event_id,
            'price' : 50
        })
        assert response.status_code == 201