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
    """Service for ensuring API request idempotency using Redis distributed locks."""

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
        """Verify idempotency state and acquire a lock for a new request.

        Checks if a request with the same idempotency key was already processed
        or is currently in progress. If processed, returns the cached response.
        If new, locks the key to prevent concurrent identical requests.

        Args:
            user_id: The ID of the user making the request.
            action: The specific API action (e.g., 'create_ticket').
            idempotency_key: A unique string provided by the client.
            payload: The request body, used to verify payload consistency.

        Returns:
            The cached response dictionary if the request was already completed,
            otherwise None (indicating the lock was acquired).

        Raises:
            IdempotencyStateError: If there's a concurrent lock conflict
            or corrupted cache.
            IdempotencyConflictError: If the payload differs from the original request
                or the original request is still processing.
        """
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
        """Save the successful response of an operation to the idempotency cache.

        Updates the Redis record to 'COMPLETED' status, storing the final response
        so subsequent identical requests can return it directly.

        Args:
            user_id: The ID of the user.
            action: The specific API action.
            idempotency_key: The unique key provided by the client.
            response_data: The JSON-serializable response to cache.
            payload: The original request payload for hash consistency.
        """
        redis_key = self._generate_key(user_id, action, idempotency_key)
        current_hash = self._hash_payload(payload)

        record = IdempotencyRecord(
            status="COMPLETED", response=response_data, payload_hash=current_hash
        )

        await self.redis.set(redis_key, record.model_dump_json(), ex=self.ttl_seconds)

    async def unlock(self, user_id: int, action: str, idempotency_key: str) -> None:
        """Release the idempotency lock.

        Typically used to clean up the lock if the underlying operation fails,
        allowing the client to safely retry the request with the same key.

        Args:
            user_id: The ID of the user.
            action: The specific API action.
            idempotency_key: The unique key provided by the client.
        """
        redis_key = self._generate_key(user_id, action, idempotency_key)
        await self.redis.delete(redis_key)
