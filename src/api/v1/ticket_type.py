from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.params import Query

from src.api.decorators import idempotent
from src.api.deps import (
    IdempotencyHeader,
    IdempotencyServiceDep,
    TicketTypeServiceDep,
    get_current_superuser,
)
from src.core import settings
from src.core.exception import EmptyUpdateDataError
from src.models import User
from src.models.ticket_type import TicketType
from src.schemas.ticket_type import (
    TicketTypeCreate,
    TicketTypeDetailResponse,
    TicketTypeResponse,
    TicketTypeUpdate,
)

router = APIRouter()


@router.post(
    "/", response_model=TicketTypeResponse, status_code=status.HTTP_201_CREATED
)
@idempotent(action="ticket_type_create")
async def ticket_type_create(
    ticket_type_data: TicketTypeCreate,
    ticket_type_service: TicketTypeServiceDep,
    admin: Annotated[User, Depends(get_current_superuser)],
    idempotency_service: IdempotencyServiceDep,
    idempotency_key: IdempotencyHeader = None,
) -> TicketType:
    return await ticket_type_service.create(ticket_type_data)


@router.get(
    "/{ticket_type_id}",
    response_model=TicketTypeDetailResponse,
    status_code=status.HTTP_200_OK,
)
async def ticket_type_get(
    ticket_type_id: int,
    ticket_type_service: TicketTypeServiceDep,
) -> TicketType:
    return await ticket_type_service.get(ticket_type_id)


@router.get(
    "/event/{event_id}",
    response_model=list[TicketTypeDetailResponse],
    status_code=status.HTTP_200_OK,
)
async def ticket_type_get_all_for_event(
    event_id: int,
    ticket_type_service: TicketTypeServiceDep,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = settings.DEFAULT_PAGE_LIMIT,
) -> Sequence[TicketType]:
    return await ticket_type_service.get_all_for_event(
        event_id=event_id, offset=offset, limit=limit
    )


@router.delete(
    "/{ticket_type_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def ticket_type_delete(
    ticket_type_id: int,
    ticket_type_service: TicketTypeServiceDep,
    admin: Annotated[User, Depends(get_current_superuser)],
) -> None:
    await ticket_type_service.delete(ticket_type_id)


@router.patch(
    "/{ticket_type_id}",
    response_model=TicketTypeResponse,
    status_code=status.HTTP_200_OK,
)
async def ticket_type_update(
    ticket_type_id: int,
    update_data: TicketTypeUpdate,
    ticket_type_service: TicketTypeServiceDep,
    admin: Annotated[User, Depends(get_current_superuser)],
) -> TicketType:
    if not update_data.model_dump(exclude_unset=True):
        raise EmptyUpdateDataError("No field provided for update")

    return await ticket_type_service.update(
        ticket_type_id=ticket_type_id, update_data=update_data
    )
