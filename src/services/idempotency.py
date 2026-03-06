from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import ValidationError
from redis.asyncio import Redis

from src.core import settings
from src.core.exception import IdempotencyConflictError, IdempotencyStateError
from src.schemas import IdempotencyRecord

if TYPE_CHECKING:
    RedisClient = Redis[Any]
else:
    RedisClient = Redis


class IdempotencyService:
    def __init__(self, redis_client: RedisClient):
        self.redis = redis_client
        self.ttl_seconds = settings.REDIS_TTL_SECONDS

    def _generate_key(self, user_id: int, action: str, idempotency_key: str) -> str:
        return f"idem:u{user_id}:{action}:{idempotency_key}"

    async def check_and_lock(
        self, user_id: int, action: str, idempotency_key: str
    ) -> dict[str, Any] | None:
        redis_key = self._generate_key(user_id, action, idempotency_key)

        initial_record = IdempotencyRecord(status="IN_PROGRESS")
        lock_acquired = await self.redis.set(
            name=redis_key,
            value=initial_record.model_dump_json(),
            ex=self.ttl_seconds,
            nx=True,
        )

        if lock_acquired:
            return None

        raw_key = await self.redis.get(redis_key)

        if not raw_key:
            raise IdempotencyStateError("Concurrent conflict. Please retry.")

        try:
            data = IdempotencyRecord.model_validate_json(raw_key)
        except ValidationError as e:
            raise IdempotencyStateError("Corrupted data in cache. Please retry.") from e

        if data.status == "IN_PROGRESS":
            raise IdempotencyConflictError("Request already in progress. Please wait.")

        return data.response

    async def save_response(
        self,
        user_id: int,
        action: str,
        idempotency_key: str,
        response_data: dict[str, Any],
    ) -> None:
        redis_key = self._generate_key(user_id, action, idempotency_key)

        record = IdempotencyRecord(status="COMPLETED", response=response_data)

        await self.redis.set(redis_key, record.model_dump_json(), ex=self.ttl_seconds)

    async def unlock(self, user_id: int, action: str, idempotency_key: str) -> None:
        redis_key = self._generate_key(user_id, action, idempotency_key)
        await self.redis.delete(redis_key)
