from typing import Any

from pydantic import BaseModel


class IdempotencyRecord(BaseModel):
    status: str
    response: dict[str, Any] | None = None
