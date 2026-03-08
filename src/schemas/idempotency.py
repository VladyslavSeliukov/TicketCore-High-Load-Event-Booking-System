from typing import Any

from pydantic import BaseModel


class IdempotencyRecord(BaseModel):
    """Internal schema for serializing idempotency state and API responses to Redis.

    Used by the IdempotencyService to track ongoing requests and cache
    the responses of successfully completed operations.
    """

    status: str
    response: dict[str, Any] | None = None
    payload_hash: str | None = None
