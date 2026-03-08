from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar, cast

from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel

from src.models import User
from src.services.idempotency import IdempotencyService

F = TypeVar("F", bound=Callable[..., Any])


def idempotent(
    action: str, key_param_name: str = "idempotency_key"
) -> Callable[[F], F]:

    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            idempotency_key = kwargs.get(key_param_name)

            user = next((v for v in kwargs.values() if isinstance(v, User)), None)
            service = next(
                (v for v in kwargs.values() if isinstance(v, IdempotencyService)), None
            )
            payload_obj = next(
                (v for v in kwargs.values() if isinstance(v, BaseModel)), None
            )
            payload = payload_obj.model_dump(mode="json") if payload_obj else None

            if not idempotency_key or not user or not service:
                return await func(*args, **kwargs)

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
