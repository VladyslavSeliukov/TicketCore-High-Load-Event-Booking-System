from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from sqlalchemy.exc import SQLAlchemyError
from starlette.responses import JSONResponse

from src.api import health
from src.api.v1 import auth, events, payment, ticket_type, tickets
from src.core import logger
from src.core.config import settings
from src.core.exception import (
    EmptyUpdateDataError,
    EventDeleteError,
    EventNotFoundError,
    HealthError,
    IdempotencyConflictError,
    IdempotencyStateError,
    InactiveUserError,
    InvalidCredentialsError,
    TicketAlreadyPaidError,
    TicketNotFoundError,
    TicketReservationExpireError,
    TicketsSoldOutError,
    TicketTypeDeleteError,
    TicketTypeNotFoundError,
    TicketTypeQuantity,
    UserAlreadyExistsError,
)
from src.db.redis import close_redis_pool, init_redis_pool


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage the application lifecycle context.

    Initializes global infrastructure connections (like the Redis pool)
    on startup and safely tears them down on application shutdown.
    """
    logger.info("Initializing Redis Pool...")
    await init_redis_pool()

    yield

    logger.info("Closing Redis pool...")
    await close_redis_pool()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

app.include_router(health.router, tags=["System"])

app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["Auth"])
app.include_router(
    tickets.router, prefix=f"{settings.API_V1_STR}/tickets", tags=["Tickets"]
)
app.include_router(
    payment.router, prefix=f"{settings.API_V1_STR}/tickets", tags=["Payments"]
)
app.include_router(
    ticket_type.router,
    prefix=f"{settings.API_V1_STR}/ticket-types",
    tags=["Ticket Types"],
)
app.include_router(
    events.router, prefix=f"{settings.API_V1_STR}/events", tags=["Events"]
)


@app.exception_handler(InvalidCredentialsError)
@app.exception_handler(InactiveUserError)
async def auth_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Intercept authentication failures and map them to HTTP 401 Unauthorized.

    Catches invalid credentials and inactive user attempts, ensuring the
    response includes the standard 'WWW-Authenticate' header required
    by OAuth2 specifications.
    """
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"detail": str(exc)},
        headers={"WWW-Authenticate": "Bearer"},
    )


@app.exception_handler(TicketTypeNotFoundError)
@app.exception_handler(TicketNotFoundError)
@app.exception_handler(EventNotFoundError)
async def not_found_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Intercept missing resource errors and map them to HTTP 404 Not Found.

    Provides a unified response format for any database queries that fail
    to locate specific events, ticket types, or individual tickets.
    """
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND, content={"detail": str(exc)}
    )


@app.exception_handler(TicketAlreadyPaidError)
@app.exception_handler(IdempotencyStateError)
@app.exception_handler(IdempotencyConflictError)
@app.exception_handler(TicketTypeQuantity)
@app.exception_handler(TicketTypeDeleteError)
@app.exception_handler(EventDeleteError)
@app.exception_handler(UserAlreadyExistsError)
@app.exception_handler(TicketsSoldOutError)
async def conflict_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Intercept business logic conflicts and map them to HTTP 409 Conflict.

    Catches specific domain errors (e.g., sold-out tickets, existing users)
    and prevents them from crashing the application, returning a clean
    client-facing error message.
    """
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT, content={"detail": str(exc)}
    )


@app.exception_handler(SQLAlchemyError)
async def internal_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch unhandled database transactions and map them to HTTP 500.

    Provides a global safety net for raw SQLAlchemy errors, hiding internal
    database structure details from the client while logging the exact failure.
    """
    logger.error(f"Global DB Error at {request.method} {request.url.path} : {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )


@app.exception_handler(TicketReservationExpireError)
@app.exception_handler(EmptyUpdateDataError)
async def empty_update_data_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """Intercept bad requests and map them to HTTP 400 Bad Request.

    Handles scenarios where the client provides invalid context for an operation,
    such as submitting an empty update payload or paying for an expired reservation.
    """
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST, content={"detail": str(exc)}
    )


@app.exception_handler(HealthError)
async def service_unavailable(request: Request, exc: Exception) -> JSONResponse:
    """Intercept infrastructure health failures and map them to HTTP 503.

    Catches domain-specific health errors (e.g., unreachable database or cache)
    and signals to the orchestrator that the instance is temporarily unavailable.
    """
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content={"detail": str(exc)}
    )
