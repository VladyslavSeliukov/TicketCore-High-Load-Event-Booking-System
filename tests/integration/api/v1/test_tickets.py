import pytest
from factories import EventFactory
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_create_event_flow(
    client: AsyncClient, db_connection: AsyncSession
) -> None:
    event = EventFactory.build()
    db_connection.add(event)
    await db_connection.commit()
    await db_connection.refresh(event)

    ticket_payload = {"event_id": event.id, "price": 500}
    response = await client.post("/api/v1/tickets/", json=ticket_payload)
    assert response.status_code == 201
    assert response.json()["event_title"] == event.title


@pytest.mark.asyncio
async def test_get_unexisted_ticket(client: AsyncClient) -> None:
    response = await client.get("/api/v1/tickets/9999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_post_ticket_with_unexisted_event(client: AsyncClient) -> None:
    ticket_payload = {"event_id": "0", "price": 50}
    response = await client.post("/api/v1/tickets/", json=ticket_payload)
    assert response.status_code == 404
