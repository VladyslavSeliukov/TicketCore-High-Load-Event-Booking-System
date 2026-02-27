from datetime import datetime

import pytest
from factories import EventFactory
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.event import Event


@pytest.mark.asyncio
class TestEventModel:
    async def test_valid(self, db_connection: AsyncSession) -> None:
        event = EventFactory.build()

        db_connection.add(event)
        await db_connection.commit()
        await db_connection.refresh(event)

        assert event.id is not None
        assert isinstance(event.id, int)
        assert event.tickets_sold == 0

    async def test_default_value(self, db_connection: AsyncSession) -> None:
        event = Event(
            title="Korn Europe Tour 2026",
            date=datetime.now(),
            country="Poland",
            city="Wroclaw",
            street_address="Sucha 1",
            tickets_quantity=50,
            # no ticket_sold
        )

        db_connection.add(event)
        await db_connection.commit()
        await db_connection.refresh(event)

        assert event.tickets_sold == 0

    async def test_boundary_values(self, db_connection: AsyncSession) -> None:
        event = EventFactory.build(tickets_quantity=100, tickets_sold=100)

        db_connection.add(event)
        await db_connection.commit()
        await db_connection.refresh(event)

        assert event.tickets_quantity == event.tickets_sold

    async def test_tickets_sold_limit(self, db_connection: AsyncSession) -> None:
        bad_event = EventFactory.build(tickets_quantity=100, tickets_sold=101)

        db_connection.add(bad_event)

        with pytest.raises(IntegrityError):
            await db_connection.commit()

        await db_connection.rollback()

    @pytest.mark.parametrize("invalid_quantity", [0, -1, -100])
    async def test_negative_ticket_quantity(
        self, db_connection: AsyncSession, invalid_quantity: int
    ) -> None:
        bad_event = EventFactory.build(tickets_quantity=invalid_quantity)

        db_connection.add(bad_event)

        with pytest.raises(IntegrityError):
            await db_connection.commit()

        await db_connection.rollback()

    @pytest.mark.parametrize("field", ["title", "country", "city", "street_address"])
    async def test_strings_length_constraint(
        self, db_connection: AsyncSession, field: str
    ) -> None:
        kwargs = {field: "a" * 101}
        event = EventFactory.build(**kwargs)

        db_connection.add(event)

        with pytest.raises(DBAPIError):
            await db_connection.commit()

        await db_connection.rollback()

    @pytest.mark.parametrize(
        "field",
        ["title", "date", "country", "city", "street_address", "tickets_quantity"],
    )
    async def test_nullable_fields(
        self, db_connection: AsyncSession, field: str
    ) -> None:
        kwargs = {field: None}
        event = EventFactory.build(**kwargs)

        db_connection.add(event)

        with pytest.raises(IntegrityError):
            await db_connection.commit()

        await db_connection.rollback()
