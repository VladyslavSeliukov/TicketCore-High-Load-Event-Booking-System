from __future__ import annotations

from typing import Annotated

import jwt
from arq import ArqRedis
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import ValidationError
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from src.core import settings
from src.core.logger import logger
from src.db.redis import get_arq_pool, get_redis
from src.db.session import get_db
from src.models import User
from src.schemas.token import TokenPayload
from src.services.auth import AuthService
from src.services.event import EventService
from src.services.idempotency import IdempotencyService
from src.services.payment import PaymentService
from src.services.ticket import TicketService
from src.services.ticket_type import TicketTypeService

RedisClient = Redis

reusable_oauth2 = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

DBDep = Annotated[AsyncSession, Depends(get_db)]
IdempotencyHeader = Annotated[
    str | None, Header(alias="Idempotency-Key", min_length=10, max_length=100)
]


async def get_current_user(
    token: Annotated[str, Depends(reusable_oauth2)], session: DBDep
) -> User:
    """Validate the JWT access token and retrieve the current user.

    Decodes the Bearer token to extract the user ID (`sub`). Verifies
    the token's signature and expiration, then fetches the corresponding
    User model from the database.

    Returns:
        The authenticated User instance.

    Raises:
        HTTPException: 401 Unauthorized if the token is missing, invalid,
            expired, or if the user no longer exists in the database.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        jwt_payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )

        token_data = TokenPayload(**jwt_payload)
        if not token_data.sub:
            logger.info('Auth failed: Token has no "sub" field')
            raise credentials_exception

    except jwt.ExpiredSignatureError as e:
        logger.info("Auth failed: Token expired")
        raise credentials_exception from e
    except (jwt.PyJWTError, ValidationError) as e:
        logger.warning(f"Auth failed: Decode error : {e}")
        raise credentials_exception from e

    try:
        user_id = int(token_data.sub)
    except ValueError as e:
        logger.warning(f"Auth failed: User Id is not an int: {token_data.sub}")
        raise credentials_exception from e

    user = await session.get(User, user_id)

    if not user:
        logger.warning(f"Auth failed: User {user_id} not found in DB")
        raise credentials_exception

    return user


async def get_current_superuser(current_user: User = Depends(get_current_user)) -> User:
    """Verify that the currently authenticated user has superuser privileges.

    Returns:
        The authenticated User instance if they are a superuser.

    Raises:
        HTTPException: 403 Forbidden if the user lacks superuser rights.
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="User doesn't have permission"
        )
    return current_user


async def get_ticket_service(
    session: DBDep, arq_pool: ArqRedis = Depends(get_arq_pool)
) -> TicketService:
    """Provide an initialized TicketService instance for dependency injection."""
    return TicketService(session, arq_pool)


async def get_event_service(session: DBDep) -> EventService:
    """Provide an initialized EventService instance for dependency injection."""
    return EventService(session)


async def get_auth_service(session: DBDep) -> AuthService:
    """Provide an initialized EventService instance for dependency injection."""
    return AuthService(session)


async def get_ticket_type_service(session: DBDep) -> TicketTypeService:
    """Provide an initialized TicketTypeService instance for dependency injection."""
    return TicketTypeService(session)


async def get_idempotency_service(
    redis: RedisClient = Depends(get_redis),
) -> IdempotencyService:
    """Provide an initialized IdempotencyService instance for dependency injection."""
    return IdempotencyService(redis)


async def get_payment_service(session: DBDep) -> PaymentService:
    """Provide an initialized PaymentService instance for dependency injection."""
    return PaymentService(session)


TicketServiceDep = Annotated[TicketService, Depends(get_ticket_service)]
EventServiceDep = Annotated[EventService, Depends(get_event_service)]
AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
TicketTypeServiceDep = Annotated[TicketTypeService, Depends(get_ticket_type_service)]
IdempotencyServiceDep = Annotated[IdempotencyService, Depends(get_idempotency_service)]
PaymentServiceDep = Annotated[PaymentService, Depends(get_payment_service)]
