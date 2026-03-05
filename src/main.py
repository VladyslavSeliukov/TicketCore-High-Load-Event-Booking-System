from fastapi import FastAPI, Request, status
from sqlalchemy.exc import SQLAlchemyError
from starlette.responses import JSONResponse

from src.api.v1 import auth, events, ticket_type, tickets
from src.core import logger
from src.core.config import settings
from src.core.exception import (
    EmptyUpdateDataError,
    EventDeleteError,
    EventNotFoundError,
    InactiveUserError,
    InvalidCredentialsError,
    TicketNotFoundError,
    TicketsSoldOutError,
    TicketTypeDeleteError,
    TicketTypeNotFoundError,
    TicketTypeQuantity,
    UserAlreadyExistsError,
)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
)

app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["Auth"])
app.include_router(
    tickets.router, prefix=f"{settings.API_V1_STR}/tickets", tags=["Tickets"]
)
app.include_router(
    events.router, prefix=f"{settings.API_V1_STR}/events", tags=["Events"]
)
app.include_router(
    ticket_type.router,
    prefix=f"{settings.API_V1_STR}/ticket_type",
    tags=["Ticket Type"],
)


@app.exception_handler(InvalidCredentialsError)
@app.exception_handler(InactiveUserError)
async def auth_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"detail": str(exc)},
        headers={"WWW-Authentication": "Bearer"},
    )


@app.exception_handler(TicketTypeNotFoundError)
@app.exception_handler(TicketNotFoundError)
@app.exception_handler(EventNotFoundError)
async def not_found_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND, content={"detail": str(exc)}
    )


@app.exception_handler(TicketTypeQuantity)
@app.exception_handler(TicketTypeDeleteError)
@app.exception_handler(EventDeleteError)
@app.exception_handler(UserAlreadyExistsError)
@app.exception_handler(TicketsSoldOutError)
async def conflict_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT, content={"detail": str(exc)}
    )


@app.exception_handler(SQLAlchemyError)
async def internal_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error(f"Global DB Error at {request.method} {request.url.path} : {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )


@app.exception_handler(EmptyUpdateDataError)
async def empty_update_data_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST, content={"detail": str(exc)}
    )


@app.get("/", tags=["System"])
async def main() -> dict[str, str]:
    return {
        "status": "healthy",
        "app": settings.PROJECT_NAME,
        "env": settings.ENVIRONMENT,
    }
