from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar, cast

from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel

from src.models import User
from src.services.idempotency import IdempotencyService

F = TypeVar("F", bound=Callable[..., Any])


def _extract_business_payload(
    kwargs: dict[str, Any], key_name: str
) -> dict[str, Any] | None:
    """Extract business data from request parameters for semantic hashing.

    Filters the endpoint's keyword arguments to build a deterministic payload
    dictionary. It explicitly includes Pydantic DTOs (request bodies) and
    primitive types (path/query parameters), while ignoring injected system
    dependencies like database sessions, services, or user objects.

    Args:
        kwargs: The keyword arguments passed to the FastAPI endpoint.
        key_name: The name of the idempotency key parameter to exclude from the hash.

    Returns:
        A dictionary containing the extracted business payload, or None if no
        relevant data is found.
    """
    payload: dict[str, Any] = {}
    for key, value in kwargs.items():
        if key == key_name:
            continue

        if isinstance(value, BaseModel):
            payload[key] = value.model_dump(mode="json")
        elif isinstance(value, (int, str, float, bool)):
            payload[key] = value

    return payload if payload else None


def idempotent(
    action: str, key_param_name: str = "idempotency_key"
) -> Callable[[F], F]:
    """Ensure API endpoint idempotency using Redis locks and semantic hashing.

    Intercepts the request to check for a valid idempotency key. It extracts
    relevant business data (DTOs and primitives) to generate a semantic hash,
    preventing collisions if the client mistakenly uses the same key for
    different operations. Queries the IdempotencyService to either return
    a cached response or lock the request to prevent concurrent duplicates.
    Automatically caches the response upon successful execution.

    Args:
        action: A unique string identifying the operation (e.g., 'create_ticket').
        key_param_name: The expected kwarg name for the idempotency key.

    Returns:
        A decorator function that wraps the FastAPI endpoint.
    """

    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            idempotency_key = kwargs.get(key_param_name)

            user = next((v for v in kwargs.values() if isinstance(v, User)), None)
            service = next(
                (v for v in kwargs.values() if isinstance(v, IdempotencyService)), None
            )

            if not idempotency_key or not user or not service:
                return await func(*args, **kwargs)

            payload = _extract_business_payload(kwargs, key_param_name)

            cached_response = await service.check_and_lock(
                user_id=user.id,
                action=action,
                idempotency_key=idempotency_key,
                payload=payload,
            )

            if cached_response is not None:
                return cached_response

            try:
                response = await func(*args, **kwargs)
                response_data = jsonable_encoder(response)

                await service.save_response(
                    user_id=user.id,
                    action=action,
                    idempotency_key=idempotency_key,
                    response_data=response_data,
                    payload=payload,
                )

                return response
            except Exception:
                await service.unlock(
                    user_id=user.id, action=action, idempotency_key=idempotency_key
                )
                raise

        return cast(F, wrapper)

    return decorator
