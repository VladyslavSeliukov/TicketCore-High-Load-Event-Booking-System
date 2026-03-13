from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.params import Query

from src.api.decorators import idempotent
from src.api.deps import (
    EventServiceDep,
    IdempotencyHeader,
    IdempotencyServiceDep,
    TicketTypeServiceDep,
    get_current_superuser,
)
from src.core.config import settings
from src.core.exception import EmptyUpdateDataError
from src.models import User
from src.schemas.event import (
    EventCreate,
    EventDetailResponse,
    EventResponse,
    EventUpdate,
)
from src.schemas.ticket_type import TicketTypeResponse

router = APIRouter()


@router.post("", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
@idempotent(action="create_event")
async def create_event(
    event: EventCreate,
    event_service: EventServiceDep,
    admin_user: Annotated[User, Depends(get_current_superuser)],
    idempotency_service: IdempotencyServiceDep,
    idempotency_key: IdempotencyHeader = None,
) -> EventResponse:
    """Create a new event. Restricted to superusers.

    This endpoint is idempotent to prevent accidental duplicate event creation.

    Args:
        event: Payload containing event details (title, date, location).
        event_service: Injected event service dependency.
        admin_user: The authenticated superuser making the request.
        idempotency_service: Injected idempotency service dependency.
        idempotency_key: Unique client-generated key.

    Returns:
        EventResponse DTO containing the newly created event details.
    """
    return await event_service.create(event_data=event)


@router.get(
    "/{event_id}", response_model=EventDetailResponse, status_code=status.HTTP_200_OK
)
async def get_event(
    event_id: int, event_service: EventServiceDep
) -> EventDetailResponse:
    """Retrieve public details of a specific event.

    Includes basic event information along with all available ticket types
    and their current pricing.

    Args:
        event_id: The unique identifier of the event.
        event_service: Injected event service dependency.

    Returns:
        The Event details and its associated ticket types.
    """
    return await event_service.get(event_id=event_id)


@router.get("", response_model=list[EventResponse], status_code=status.HTTP_200_OK)
async def get_events(
    event_service: EventServiceDep,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = settings.DEFAULT_PAGE_LIMIT,
) -> Sequence[EventResponse]:
    """Retrieve a paginated list of all events.

    Args:
        event_service: Injected event service dependency.
        offset: The number of items to skip.
        limit: The maximum number of items to return per page.

    Returns:
        A list of EventResponse DTOs.
    """
    return await event_service.get_all(offset=offset, limit=limit)


@router.get(
    "/{event_id}/ticket-types",
    response_model=list[TicketTypeResponse],
    status_code=status.HTTP_200_OK,
)
async def ticket_type_get_all_for_event(
    event_id: int,
    ticket_type_service: TicketTypeServiceDep,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = settings.DEFAULT_PAGE_LIMIT,
) -> Sequence[TicketTypeResponse]:
    """Retrieve a paginated list of all ticket types for a specific event.

    Args:
        event_id: The ID of the target event.
        ticket_type_service: Injected ticket type service dependency.
        offset: Number of items to skip.
        limit: Maximum number of items to return per page.

    Returns:
        A list of TicketTypeResponse DTOs associated with the event.
    """
    return await ticket_type_service.get_all_for_event(
        event_id=event_id, offset=offset, limit=limit
    )


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(
    event_id: int,
    event_service: EventServiceDep,
    admin_user: Annotated[User, Depends(get_current_superuser)],
) -> None:
    """Delete an existing event. Restricted to superusers.

    Cannot be performed if tickets have already been reserved or sold
    for this event.

    Args:
        event_id: The unique identifier of the event to delete.
        event_service: Injected event service dependency.
        admin_user: The authenticated superuser making the request.
    """
    await event_service.delete(event_id)


@router.patch(
    "/{event_id}", response_model=EventResponse, status_code=status.HTTP_200_OK
)
async def update_event(
    event_id: int,
    update_data: EventUpdate,
    event_service: EventServiceDep,
    admin_user: Annotated[User, Depends(get_current_superuser)],
) -> EventResponse:
    """Update specific attributes of an event. Restricted to superusers.

    Only the fields provided in the payload will be updated; unset fields
    will remain unchanged.

    Args:
        event_id: The unique identifier of the event to update.
        update_data: Payload containing the fields to modify.
        event_service: Injected event service dependency.
        admin_user: The authenticated superuser making the request.

    Returns:
        EventResponse DTO containing the updated event.

    Raises:
        EmptyUpdateDataError: If the request payload contains no valid fields.
    """
    if not update_data.model_dump(exclude_unset=True):
        raise EmptyUpdateDataError("No field provided for update")
    return await event_service.update(event_id=event_id, update_data=update_data)
