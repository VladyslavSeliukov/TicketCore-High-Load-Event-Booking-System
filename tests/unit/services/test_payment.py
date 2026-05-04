from unittest.mock import ANY, AsyncMock

import pytest
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exception import (
    TicketAlreadyPaidError,
    TicketNotFoundError,
    TicketReservationExpireError,
)
from src.models import Ticket
from src.models.ticket import TicketStatus
from src.schemas.payment import TicketPaymentSchema
from src.services.payment import PaymentService


@pytest.mark.asyncio
class TestPayForTicket:
    async def test_success(self) -> None:
        mock_db: AsyncMock = AsyncMock(spec=AsyncSession)
        mock_redis: AsyncMock = AsyncMock()

        fake_ticket = Ticket(
            id=1, owner_id=1, ticket_type_id=1, status=TicketStatus.RESERVED
        )
        mock_db.scalar.return_value = fake_ticket
        mock_payment_service = PaymentService(session=mock_db, redis=mock_redis)

        result = await mock_payment_service.pay_for_ticket(ticket_id=1, owner_id=1)

        assert result is not None
        assert isinstance(result, TicketPaymentSchema)
        assert fake_ticket.status == TicketStatus.SOLD

        mock_db.scalar.assert_awaited_once_with(ANY)
        mock_db.commit.assert_awaited_once()
        mock_db.refresh.assert_awaited_once_with(fake_ticket)
        mock_redis.hdel.assert_awaited_once_with(ANY, "1")

    async def test_not_found(self) -> None:
        mock_db: AsyncMock = AsyncMock(spec=AsyncSession)
        mock_redis: AsyncMock = AsyncMock()

        mock_db.scalar.return_value = None
        mock_payment_service = PaymentService(session=mock_db, redis=mock_redis)

        with pytest.raises(TicketNotFoundError) as exc_info:
            await mock_payment_service.pay_for_ticket(ticket_id=1, owner_id=1)

        assert "Ticket not found" in str(exc_info.value)
        mock_db.scalar.assert_awaited_once_with(ANY)

        mock_db.commit.assert_not_called()
        mock_db.refresh.assert_not_called()
        mock_redis.hdel.assert_not_called()

    async def test_already_paid(self) -> None:
        mock_db: AsyncMock = AsyncMock(spec=AsyncSession)
        mock_redis: AsyncMock = AsyncMock()

        fake_ticket = Ticket(
            id=1, owner_id=1, ticket_type_id=1, status=TicketStatus.SOLD
        )
        mock_db.scalar.return_value = fake_ticket
        mock_payment_service = PaymentService(session=mock_db, redis=mock_redis)

        with pytest.raises(TicketAlreadyPaidError) as exc_info:
            await mock_payment_service.pay_for_ticket(ticket_id=1, owner_id=1)

        assert "This ticket is already paid" in str(exc_info.value)
        mock_db.scalar.assert_awaited_once_with(ANY)

        mock_db.commit.assert_not_called()
        mock_db.refresh.assert_not_called()
        mock_redis.hdel.assert_not_called()

    async def test_canceled(self) -> None:
        mock_db: AsyncMock = AsyncMock(spec=AsyncSession)
        mock_redis: AsyncMock = AsyncMock()

        fake_ticket = Ticket(
            id=1, owner_id=1, ticket_type_id=1, status=TicketStatus.CANCELED
        )
        mock_db.scalar.return_value = fake_ticket
        mock_payment_service = PaymentService(session=mock_db, redis=mock_redis)

        with pytest.raises(TicketReservationExpireError) as exc_info:
            await mock_payment_service.pay_for_ticket(ticket_id=1, owner_id=1)

        assert "Reservation time expired" in str(exc_info.value)
        mock_db.scalar.assert_awaited_once_with(ANY)

        mock_db.commit.assert_not_called()
        mock_db.refresh.assert_not_called()
        mock_redis.hdel.assert_not_called()

    async def test_db_went_down_on_scalar(self) -> None:
        mock_db: AsyncMock = AsyncMock(spec=AsyncSession)
        mock_redis: AsyncMock = AsyncMock()

        mock_db.scalar.side_effect = SQLAlchemyError("Database connection lost")
        mock_payment_service = PaymentService(session=mock_db, redis=mock_redis)

        with pytest.raises(SQLAlchemyError) as exc_info:
            await mock_payment_service.pay_for_ticket(ticket_id=1, owner_id=1)

        mock_db.scalar.assert_awaited_once_with(ANY)

        assert "Database connection lost" in str(exc_info.value)

        mock_db.commit.assert_not_called()
        mock_db.rollback.assert_not_called()
        mock_db.refresh.assert_not_called()
        mock_redis.hdel.assert_not_called()

    async def test_db_went_down_on_commit(self) -> None:
        mock_db: AsyncMock = AsyncMock(spec=AsyncSession)
        mock_redis: AsyncMock = AsyncMock()

        fake_ticket = Ticket(
            id=1, owner_id=1, ticket_type_id=1, status=TicketStatus.RESERVED
        )
        mock_db.scalar.return_value = fake_ticket
        mock_db.commit.side_effect = SQLAlchemyError("Database connection lost")
        mock_payment_service = PaymentService(session=mock_db, redis=mock_redis)

        with pytest.raises(SQLAlchemyError) as exc_info:
            await mock_payment_service.pay_for_ticket(ticket_id=1, owner_id=1)

        assert "Database connection lost" in str(exc_info.value)
        mock_db.scalar.assert_awaited_once_with(ANY)
        mock_db.commit.assert_awaited_once()

        mock_db.rollback.assert_awaited_once()
        mock_db.refresh.assert_not_called()
        mock_redis.hdel.assert_not_called()
