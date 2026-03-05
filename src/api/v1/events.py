from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.params import Query

from src.api.decorators import idempotent
from src.api.deps import (
    EventServiceDep,
    IdempotencyHeader,
    IdempotencyServiceDep,
    get_current_superuser,
)
from src.core.config import settings
from src.core.exception import EmptyUpdateDataError
from src.models import Event, User
from src.schemas.event import (
    EventCreate,
    EventDetailResponse,
    EventResponse,
    EventUpdate,
)

router = APIRouter()


@router.post("/", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
@idempotent(action="create_ticket")
async def create_event(
    event: EventCreate,
    event_service: EventServiceDep,
    admin_user: Annotated[User, Depends(get_current_superuser)],
    idempotency_service: IdempotencyServiceDep,
    idempotency_key: IdempotencyHeader = None,
) -> Event:
    return await event_service.create(event_data=event)


@router.get(
    "/{event_id}", response_model=EventDetailResponse, status_code=status.HTTP_200_OK
)
async def get_event(event_id: int, event_service: EventServiceDep) -> Event:
    return await event_service.get(event_id=event_id)


@router.get(
    "/", response_model=list[EventDetailResponse], status_code=status.HTTP_200_OK
)
async def get_events(
    event_service: EventServiceDep,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = settings.DEFAULT_PAGE_LIMIT,
) -> Sequence[Event]:
    return await event_service.get_all(offset=offset, limit=limit)


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(
    event_id: int,
    event_service: EventServiceDep,
    admin_user: Annotated[User, Depends(get_current_superuser)],
) -> None:
    await event_service.delete(event_id)


@router.patch(
    "/{event_id}", response_model=EventResponse, status_code=status.HTTP_200_OK
)
async def update_event(
    event_id: int,
    update_data: EventUpdate,
    event_service: EventServiceDep,
    admin_user: Annotated[User, Depends(get_current_superuser)],
) -> Event:
    if not update_data.model_dump(exclude_unset=True):
        raise EmptyUpdateDataError("No field provided for update")
    return await event_service.update(event_id=event_id, update_data=update_data)
