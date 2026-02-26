import asyncio

import pytest
from factories import EventFactory
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncConnection


@pytest.mark.asyncio
async def test_race_condition_overselling(
    client: AsyncClient, db_connection: AsyncConnection
) -> None:
    event = EventFactory.build(tickets_quantity=5)
    db_connection.add(event)
    await db_connection.commit()
    await db_connection.refresh(event)

    ticket_payload = {"event_id": event.id, "price": 100}

    async def buy_ticket() -> None:
        return await client.post("/api/v1/tickets/", json=ticket_payload)

    buy_ticket_task = [buy_ticket() for _ in range(20)]
    buy_ticket_response = await asyncio.gather(*buy_ticket_task)

    success_count = sum(1 for r in buy_ticket_response if r.status_code == 201)
    conflict_count = sum(1 for r in buy_ticket_response if r.status_code == 409)

    assert success_count == 5
    assert conflict_count == 15
