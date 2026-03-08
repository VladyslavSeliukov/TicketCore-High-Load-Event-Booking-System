from __future__ import annotations

import hashlib
import json
from typing import Any

from pydantic import ValidationError
from redis.asyncio import Redis

from src.core import settings
from src.core.exception import IdempotencyConflictError, IdempotencyStateError
from src.schemas import IdempotencyRecord

RedisClient = Redis


class IdempotencyService:
    def __init__(self, redis_client: RedisClient):
        self.redis = redis_client
        self.ttl_seconds = settings.REDIS_TTL_SECONDS

    def _generate_key(self, user_id: int, action: str, idempotency_key: str) -> str:
        return f"idem:u{user_id}:{action}:{idempotency_key}"

    def _hash_payload(self, payload: dict[str, Any] | None) -> str:
        if not payload:
            return hashlib.sha256(b"").hexdigest()

        payload_bytes = json.dumps(payload, sort_keys=True).encode("utf-8")
        return hashlib.sha256(payload_bytes).hexdigest()

    async def check_and_lock(
        self,
        user_id: int,
        action: str,
        idempotency_key: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        redis_key = self._generate_key(user_id, action, idempotency_key)
        current_hash = self._hash_payload(payload)

        initial_record = IdempotencyRecord(
            status="IN_PROGRESS", payload_hash=current_hash
        )
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

        if data.payload_hash != current_hash:
            raise IdempotencyConflictError(
                "Idempotency key already used with a different payload."
            )

        if data.status == "IN_PROGRESS":
            raise IdempotencyConflictError("Request already in progress. Please wait.")

        return data.response

    async def save_response(
        self,
        user_id: int,
        action: str,
        idempotency_key: str,
        response_data: dict[str, Any],
        payload: dict[str, Any] | None = None,
    ) -> None:
        redis_key = self._generate_key(user_id, action, idempotency_key)
        current_hash = self._hash_payload(payload)

        record = IdempotencyRecord(
            status="COMPLETED", response=response_data, payload_hash=current_hash
        )

        await self.redis.set(redis_key, record.model_dump_json(), ex=self.ttl_seconds)

    async def unlock(self, user_id: int, action: str, idempotency_key: str) -> None:
        redis_key = self._generate_key(user_id, action, idempotency_key)
        await self.redis.delete(redis_key)
