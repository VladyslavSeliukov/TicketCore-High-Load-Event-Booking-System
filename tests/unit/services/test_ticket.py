from unittest.mock import ANY, AsyncMock, MagicMock

import pytest
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core import settings
from src.core.exception import (
    TicketNotFoundError,
    TicketsSoldOutError,
    TicketTypeNotFoundError,
)
from src.core.redis_keys import RedisKeys
from src.models import TicketType
from src.models.ticket import Ticket, TicketStatus
from src.schemas import TicketCreate
from src.schemas.ticket import TicketDetailResponse, TicketResponse
from src.services.ticket import TicketService


@pytest.mark.asyncio
class TestTicketCreate:
    async def test_success(self) -> None:
        mock_db: AsyncMock = AsyncMock(spec=AsyncSession)
        mock_arq_pool: AsyncMock = AsyncMock()
        mock_redis: AsyncMock = AsyncMock()
        mock_db.add = MagicMock()

        mock_redis.eval.return_value = 1

        def mock_refresh_behavior(instance: Ticket) -> None:
            instance.id = 1
            instance.status = TicketStatus.RESERVED

        mock_db.add.side_effect = mock_refresh_behavior

        mock_ticket_service: TicketService = TicketService(
            session=mock_db, arq_pool=mock_arq_pool, redis=mock_redis
        )
        ticket_payload = TicketCreate(ticket_type_id=1)

        result = await mock_ticket_service.create(user_id=1, ticket_data=ticket_payload)

        assert result.ticket_type_id == 1
        assert result.id == 1
        assert result.status == TicketStatus.RESERVED

        mock_db.execute.assert_awaited_once()
        mock_db.add.assert_called_once()
        mock_db.flush.assert_awaited_once()
        mock_db.commit.assert_awaited_once()
        mock_db.refresh.assert_awaited_once()

        mock_redis.hset.assert_awaited_once_with(ANY, "1", ANY)

        mock_arq_pool.enqueue_job.assert_awaited_once_with(
            "release_unpaid_ticket",
            1,
            _defer_by=settings.TICKET_RESERVATION_TIME_SECONDS,
        )

    async def test_redis_sold_out(self) -> None:
        mock_db: AsyncMock = AsyncMock(spec=AsyncSession)
        mock_arq_pool: AsyncMock = AsyncMock()
        mock_redis: AsyncMock = AsyncMock()

        mock_redis.eval.return_value = 0

        mock_ticket_service: TicketService = TicketService(
            session=mock_db, arq_pool=mock_arq_pool, redis=mock_redis
        )

        ticket_payload = TicketCreate(ticket_type_id=1)

        with pytest.raises(TicketsSoldOutError):
            await mock_ticket_service.create(user_id=1, ticket_data=ticket_payload)

        mock_redis.eval.assert_awaited_once()
        mock_db.get.assert_not_called()
        mock_db.execute.assert_not_called()
        mock_db.add.assert_not_called()
        mock_arq_pool.enqueue_job.assert_not_called()

    async def test_ticket_not_found(self) -> None:
        mock_db: AsyncMock = AsyncMock(spec=AsyncSession)
        mock_arg_pool: AsyncMock = AsyncMock()
        mock_redis: AsyncMock = AsyncMock()

        mock_redis.eval.return_value = -1
        mock_db.get.return_value = None

        mock_ticket_service: TicketService = TicketService(
            session=mock_db, arq_pool=mock_arg_pool, redis=mock_redis
        )

        ticket_payload = TicketCreate(ticket_type_id=1)

        with pytest.raises(TicketTypeNotFoundError):
            await mock_ticket_service.create(user_id=1, ticket_data=ticket_payload)

        mock_redis.eval.assert_awaited_once()
        mock_db.get.assert_awaited_once()
        mock_db.execute.assert_not_called()

    async def test_race_condition(self) -> None:
        mock_db: AsyncMock = AsyncMock(spec=AsyncSession)
        mock_arg_pool: AsyncMock = AsyncMock()
        mock_redis: AsyncMock = AsyncMock()

        mock_redis.eval.return_value = 1
        mock_db.add = MagicMock()
        mock_db.flush.side_effect = IntegrityError(
            statement="UPDATE ticket_types...",
            params={},
            orig=Exception("checkviolation"),
        )

        mock_ticket_service = TicketService(
            session=mock_db, arq_pool=mock_arg_pool, redis=mock_redis
        )
        ticket_payload = TicketCreate(ticket_type_id=1)
        expected_key = RedisKeys.ticket_type_inventory(1)

        with pytest.raises(TicketsSoldOutError):
            await mock_ticket_service.create(user_id=1, ticket_data=ticket_payload)

        mock_db.rollback.assert_awaited_once()
        mock_redis.incr.assert_awaited_once_with(expected_key)
        mock_arg_pool.enqueue_job.assert_not_called()

    async def test_db_wend_down(self) -> None:
        mock_db: AsyncMock = AsyncMock(spec=AsyncSession)
        mock_arg_pool: AsyncMock = AsyncMock()
        mock_redis: AsyncMock = AsyncMock()

        mock_redis.eval.return_value = 1
        mock_db.add = MagicMock()
        mock_db.flush.side_effect = SQLAlchemyError("Database connection lost")

        mock_ticket_service: TicketService = TicketService(
            session=mock_db, arq_pool=mock_arg_pool, redis=mock_redis
        )

        ticket_payload: TicketCreate = TicketCreate(ticket_type_id=1)
        expected_key = RedisKeys.ticket_type_inventory(1)

        with pytest.raises(SQLAlchemyError) as exc_info:
            await mock_ticket_service.create(user_id=1, ticket_data=ticket_payload)

        assert "Database connection lost" in str(exc_info.value)

        mock_db.rollback.assert_awaited_once()
        mock_redis.incr.assert_awaited_once_with(expected_key)
        mock_arg_pool.enqueue_job.assert_not_called()


@pytest.mark.asyncio
class TestTicketGet:
    async def test_success(self) -> None:
        mock_db: AsyncMock = AsyncMock(spec=AsyncSession)
        mock_arg_pool: AsyncMock = AsyncMock()
        mock_redis: AsyncMock = AsyncMock()

        fake_ticket = Ticket(
            id=1,
            owner_id=1,
            ticket_type_id=1,
            status=TicketStatus.RESERVED,
            ticket_type=TicketType(id=1, name="VIP"),
        )
        mock_db.scalar.return_value = fake_ticket

        mock_ticket_service: TicketService = TicketService(
            session=mock_db, arq_pool=mock_arg_pool, redis=mock_redis
        )

        result = await mock_ticket_service.get(owner_id=1, ticket_id=1)

        assert result is not None
        assert isinstance(result, TicketDetailResponse)
        assert result.id == 1
        assert result.ticket_type_id == 1
        assert result.status == TicketStatus.RESERVED

        mock_db.scalar.assert_awaited_once()

    async def test_not_found(self) -> None:
        mock_db: AsyncMock = AsyncMock(spec=AsyncSession)
        mock_arg_pool: AsyncMock = AsyncMock()
        mock_redis: AsyncMock = AsyncMock()

        mock_db.scalar.return_value = None

        mock_ticket_service: TicketService = TicketService(
            session=mock_db, arq_pool=mock_arg_pool, redis=mock_redis
        )

        with pytest.raises(TicketNotFoundError):
            await mock_ticket_service.get(owner_id=1, ticket_id=1)

        mock_db.scalar.assert_awaited_once_with(ANY)

    async def test_db_went_down(self) -> None:
        mock_db: AsyncMock = AsyncMock(spec=AsyncSession)
        mock_arg_pool: AsyncMock = AsyncMock()
        mock_redis: AsyncMock = AsyncMock()

        mock_db.scalar.side_effect = SQLAlchemyError("Database connection lost")

        mock_ticket_service: TicketService = TicketService(
            session=mock_db, arq_pool=mock_arg_pool, redis=mock_redis
        )

        with pytest.raises(SQLAlchemyError) as exc_info:
            await mock_ticket_service.get(owner_id=1, ticket_id=1)

        assert "Database connection lost" in str(exc_info.value)


@pytest.mark.asyncio
class TestTicketGetAllForUser:
    async def test_success(self) -> None:
        mock_db: AsyncMock = AsyncMock(spec=AsyncSession)
        mock_arg_pool: AsyncMock = AsyncMock()
        mock_redis: AsyncMock = AsyncMock()

        fake_ticket_1 = Ticket(id=1, owner_id=1, ticket_type_id=1, status="RESERVED")
        fake_ticket_2 = Ticket(id=2, owner_id=1, ticket_type_id=2, status="SOLD")
        mock_result = MagicMock()

        mock_result.all.return_value = [fake_ticket_1, fake_ticket_2]
        mock_db.scalars.return_value = mock_result

        mock_ticket_service: TicketService = TicketService(
            session=mock_db, arq_pool=mock_arg_pool, redis=mock_redis
        )

        result = await mock_ticket_service.get_all_for_user(
            owner_id=1, offset=0, limit=10
        )

        assert len(result) == 2
        assert isinstance(result[0], TicketResponse)

        mock_db.scalars.assert_awaited_once_with(ANY)
        mock_result.all.assert_called_once()

    async def test_not_found(self) -> None:
        mock_db: AsyncMock = AsyncMock(spec=AsyncSession)
        mock_arg_pool: AsyncMock = AsyncMock()
        mock_redis: AsyncMock = AsyncMock()

        mock_result = MagicMock()
        mock_result.all.return_value = []

        mock_db.scalars.return_value = mock_result

        mock_ticket_service: TicketService = TicketService(
            session=mock_db, arq_pool=mock_arg_pool, redis=mock_redis
        )

        result = await mock_ticket_service.get_all_for_user(
            owner_id=1, offset=0, limit=10
        )

        assert len(result) == 0
        assert isinstance(result, list)

        mock_db.scalars.assert_called_once_with(ANY)
        mock_result.all.assert_called_once()

    async def test_db_went_down(self) -> None:
        mock_db: AsyncMock = AsyncMock(spec=AsyncSession)
        mock_arg_pool: AsyncMock = AsyncMock()
        mock_redis: AsyncMock = AsyncMock()

        mock_db.scalars.side_effect = SQLAlchemyError("Database connection lost")

        mock_ticket_service: TicketService = TicketService(
            session=mock_db, arq_pool=mock_arg_pool, redis=mock_redis
        )

        with pytest.raises(SQLAlchemyError) as exc_info:
            await mock_ticket_service.get_all_for_user(owner_id=1, offset=0, limit=10)

        assert "Database connection lost" in str(exc_info.value)
        mock_db.scalars.assert_awaited_once_with(ANY)


@pytest.mark.asyncio
class TestTicketDelete:
    async def test_success(self) -> None:
        mock_db: AsyncMock = AsyncMock(spec=AsyncSession)
        mock_arg_pool: AsyncMock = AsyncMock()
        mock_redis: AsyncMock = AsyncMock()

        mock_db.execute.return_value = None

        mock_ticket_service: TicketService = TicketService(
            session=mock_db, arq_pool=mock_arg_pool, redis=mock_redis
        )

        await mock_ticket_service.delete(owner_id=1, ticket_id=1)

        mock_db.scalar.assert_awaited_once_with(ANY)
        mock_db.execute.assert_awaited_once_with(ANY)
        mock_db.delete.assert_awaited_once_with(ANY)
        mock_db.commit.assert_awaited_once()

    async def test_not_found(self) -> None:
        mock_db: AsyncMock = AsyncMock(spec=AsyncSession)
        mock_arg_pool: AsyncMock = AsyncMock()
        mock_redis: AsyncMock = AsyncMock()

        mock_db.scalar.return_value = None

        mock_ticket_service: TicketService = TicketService(
            session=mock_db, arq_pool=mock_arg_pool, redis=mock_redis
        )

        with pytest.raises(TicketNotFoundError):
            await mock_ticket_service.delete(owner_id=1, ticket_id=1)

        mock_db.scalar.assert_awaited_once_with(ANY)
        mock_db.execute.assert_not_called()

    async def test_db_went_down(self) -> None:
        mock_db: AsyncMock = AsyncMock(spec=AsyncSession)
        mock_arg_pool: AsyncMock = AsyncMock()
        mock_redis: AsyncMock = AsyncMock()

        mock_db.scalar.side_effect = SQLAlchemyError("Database connection lost")

        mock_ticket_service: TicketService = TicketService(
            session=mock_db, arq_pool=mock_arg_pool, redis=mock_redis
        )

        with pytest.raises(SQLAlchemyError) as exc_info:
            await mock_ticket_service.delete(owner_id=1, ticket_id=1)

        assert "Database connection lost" in str(exc_info.value)
        mock_db.scalar.assert_awaited_once_with(ANY)
        mock_db.execute.assert_not_called()
