from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, status
from fastapi.params import Depends, Query

from src.api.decorators import idempotent
from src.api.deps import (
    IdempotencyHeader,
    IdempotencyServiceDep,
    TicketServiceDep,
    get_current_user,
)
from src.core.config import settings
from src.models import User
from src.schemas.ticket import TicketCreate, TicketDetailResponse, TicketResponse

router = APIRouter()


@router.post("/", response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
@idempotent(action="create_ticket")
async def create_ticket(
    owner: Annotated[User, Depends(get_current_user)],
    ticket: TicketCreate,
    ticket_service: TicketServiceDep,
    idempotency_service: IdempotencyServiceDep,
    idempotency_key: IdempotencyHeader = None,
) -> TicketResponse:
    """Reserve a ticket for a specific event.

    Creates a temporary ticket reservation and locks the corresponding inventory.
    This endpoint is idempotent; repeating the request with the same
    Idempotency-Key header will safely return the cached response.

    Args:
        owner: The authenticated user making the reservation.
        ticket: Payload containing the target ticket type ID.
        ticket_service: Injected ticket service dependency.
        idempotency_service: Injected idempotency service dependency.
        idempotency_key: Unique client-generated key to prevent duplicate bookings.

    Returns:
        TicketResponse DTO containing the newly reserved ticket details.
    """
    return await ticket_service.create(user_id=owner.id, ticket_data=ticket)


@router.get(
    "/{ticket_id}", response_model=TicketDetailResponse, status_code=status.HTTP_200_OK
)
async def get_ticket(
    owner: Annotated[User, Depends(get_current_user)],
    ticket_id: int,
    ticket_service: TicketServiceDep,
) -> TicketDetailResponse:
    """Retrieve detailed information about a specific ticket.

    Includes nested information about the ticket type and the event.
    Users can only access their own tickets.

    Args:
        owner: The authenticated user requesting the ticket.
        ticket_id: The unique identifier of the ticket.
        ticket_service: Injected ticket service dependency.

    Returns:
        TicketDetailResponse DTO including nested event and ticket type relations.
    """
    return await ticket_service.get(owner_id=owner.id, ticket_id=ticket_id)


@router.get("/", response_model=list[TicketResponse], status_code=status.HTTP_200_OK)
async def get_tickets(
    owner: Annotated[User, Depends(get_current_user)],
    ticket_service: TicketServiceDep,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = settings.DEFAULT_PAGE_LIMIT,
) -> Sequence[TicketResponse]:
    """Retrieve a paginated list of all tickets owned by the current user.

    Args:
        owner: The authenticated user making the request.
        ticket_service: Injected ticket service dependency.
        offset: The number of items to skip (for pagination).
        limit: The maximum number of items to return per page.

    Returns:
        A list of TicketResponse DTOs owned by the user.
    """
    return await ticket_service.get_all_for_user(
        owner_id=owner.id, offset=offset, limit=limit
    )


@router.delete("/{ticket_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ticket(
    owner: Annotated[User, Depends(get_current_user)],
    ticket_id: int,
    ticket_service: TicketServiceDep,
) -> None:
    """Cancel a ticket reservation.

    Deletes the ticket record and releases the reserved slot back into
    the event's available inventory. Users can only cancel their own tickets.

    Args:
        owner: The authenticated user canceling the ticket.
        ticket_id: The unique identifier of the ticket to cancel.
        ticket_service: Injected ticket service dependency.
    """
    await ticket_service.delete(owner_id=owner.id, ticket_id=ticket_id)
