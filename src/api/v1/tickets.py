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
from src.models import Ticket, User
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
) -> Ticket:
    return await ticket_service.create(user_id=owner.id, ticket_data=ticket)


@router.get(
    "/{ticket_id}", response_model=TicketDetailResponse, status_code=status.HTTP_200_OK
)
async def get_ticket(
    owner: Annotated[User, Depends(get_current_user)],
    ticket_id: int,
    ticket_service: TicketServiceDep,
) -> Ticket:
    return await ticket_service.get(owner_id=owner.id, ticket_id=ticket_id)


@router.get(
    "/", response_model=list[TicketDetailResponse], status_code=status.HTTP_200_OK
)
async def get_tickets(
    owner: Annotated[User, Depends(get_current_user)],
    ticket_service: TicketServiceDep,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = settings.DEFAULT_PAGE_LIMIT,
) -> Sequence[Ticket]:
    return await ticket_service.get_all_for_user(
        owner_id=owner.id, offset=offset, limit=limit
    )


@router.delete("/{ticket_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ticket(
    owner: Annotated[User, Depends(get_current_user)],
    ticket_id: int,
    ticket_service: TicketServiceDep,
) -> None:
    await ticket_service.delete(owner_id=owner.id, ticket_id=ticket_id)
