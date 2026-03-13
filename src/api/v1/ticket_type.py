from typing import Annotated

from fastapi import APIRouter, Depends, status

from src.api.decorators import idempotent
from src.api.deps import (
    IdempotencyHeader,
    IdempotencyServiceDep,
    TicketTypeServiceDep,
    get_current_superuser,
)
from src.core.exception import EmptyUpdateDataError
from src.models import User
from src.schemas.ticket_type import (
    TicketTypeCreate,
    TicketTypeDetailResponse,
    TicketTypeResponse,
    TicketTypeUpdate,
)

router = APIRouter()


@router.post("", response_model=TicketTypeResponse, status_code=status.HTTP_201_CREATED)
@idempotent(action="ticket_type_create")
async def ticket_type_create(
    ticket_type_data: TicketTypeCreate,
    ticket_type_service: TicketTypeServiceDep,
    admin: Annotated[User, Depends(get_current_superuser)],
    idempotency_service: IdempotencyServiceDep,
    idempotency_key: IdempotencyHeader = None,
) -> TicketTypeResponse:
    """Create a new ticket type for an event. Restricted to superusers.

    This endpoint is idempotent to prevent duplicate ticket types
    from being created in case of network retries.

    Args:
        ticket_type_data: Payload containing price, quantity, and event ID.
        ticket_type_service: Injected ticket type service dependency.
        admin: The authenticated superuser making the request.
        idempotency_service: Injected idempotency service dependency.
        idempotency_key: Unique client-generated key.

    Returns:
        TicketTypeResponse DTO containing the newly created ticket type.
    """
    return await ticket_type_service.create(
        event_id=ticket_type_data.event_id, type_data=ticket_type_data
    )


@router.get(
    "/{ticket_type_id}",
    response_model=TicketTypeDetailResponse,
    status_code=status.HTTP_200_OK,
)
async def ticket_type_get(
    ticket_type_id: int,
    ticket_type_service: TicketTypeServiceDep,
) -> TicketTypeDetailResponse:
    """Retrieve details of a specific ticket type.

    Args:
        ticket_type_id: The unique identifier of the ticket type.
        ticket_type_service: Injected ticket type service dependency.

    Returns:
        TicketTypeDetailResponse DTO containing the ticket type details.
    """
    return await ticket_type_service.get(ticket_type_id)


@router.delete(
    "/{ticket_type_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def ticket_type_delete(
    ticket_type_id: int,
    ticket_type_service: TicketTypeServiceDep,
    admin: Annotated[User, Depends(get_current_superuser)],
) -> None:
    """Delete a specific ticket type. Restricted to superusers.

    Args:
        ticket_type_id: The unique identifier of the ticket type to delete.
        ticket_type_service: Injected ticket type service dependency.
        admin: The authenticated superuser making the request.
    """
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
) -> TicketTypeResponse:
    """Update specific attributes of a ticket type. Restricted to superusers.

    Only the fields provided in the payload will be updated; unset fields
    will remain unchanged.

    Args:
        ticket_type_id: The unique identifier of the ticket type to update.
        update_data: Payload containing the fields to modify.
        ticket_type_service: Injected ticket type service dependency.
        admin: The authenticated superuser making the request.

    Returns:
        TicketTypeResponse DTO containing the updated ticket type.

    Raises:
        EmptyUpdateDataError: If the request payload contains no valid fields.
    """
    if not update_data.model_dump(exclude_unset=True):
        raise EmptyUpdateDataError("No field provided for update")

    return await ticket_type_service.update(
        ticket_type_id=ticket_type_id, update_data=update_data
    )
