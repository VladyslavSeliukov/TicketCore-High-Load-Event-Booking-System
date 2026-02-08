import pytest
from fastapi import status
from sqlalchemy import select

from factories import EventPayloadFactory
from src.models import Event


@pytest.mark.asyncio
async def test_create_event_by_superuser(db_connection, authorized_superuser):
    event_model = EventPayloadFactory.build()
    event_dict = event_model.model_dump(mode='json')

    response = await authorized_superuser.post('/api/v1/events/', json = event_dict)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()

    assert data['title'] == event_model.title
    assert data['tickets_quantity'] == event_model.tickets_quantity

    query = select(Event).where(Event.title == event_model.title)
    result = await db_connection.execute(query)
    found_event = result.scalar_one_or_none()
    assert found_event is not None

@pytest.mark.asyncio
async def test_create_event_by_user(db_connection, authorized_client):
    event_model = EventPayloadFactory.build()
    event_dict = event_model.model_dump(mode='json')

    response = await authorized_client.post('/api/v1/events/', json = event_dict)
    assert response.status_code == status.HTTP_403_FORBIDDEN

    assert "User doesn't have permission" in response.json().get('detail')

    query = select(Event).where(Event.title == event_model.title)
    result = await db_connection.execute(query)
    found_event = result.scalar_one_or_none()
    assert found_event is None

@pytest.mark.asyncio
async def test_create_event_without_token(client):
    event_model = EventPayloadFactory.build()
    event_dict = event_model.model_dump(mode='json')

    response = await client.post('/api/v1/events/', json=event_dict)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

@pytest.mark.asyncio
async def test_create_event_with_negative_ticket_quality(authorized_superuser):
    event_model = EventPayloadFactory.build()
    event_dict = event_model.model_dump(mode='json')
    event_dict['tickets_quantity'] = -10

    response = await authorized_superuser.post('/api/v1/events/', json = event_dict)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    error_detail = response.json()

    assert any(err['loc'][-1] == 'tickets_quantity' for err in error_detail['detail'])