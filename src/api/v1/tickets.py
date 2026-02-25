from fastapi import APIRouter, HTTPException, status
from fastapi.params import Depends
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from src.api.deps import DBDep, get_current_user
from src.schemas.ticket import TicketCreate, TicketResponse, TicketUpdate
from src.core.config import settings
from src.models import Event, Ticket, User
from src.core.logger import logger

router = APIRouter()


@router.post("/", response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
async def create_ticket(
    ticket: TicketCreate, db: DBDep, user: User = Depends(get_current_user)
):

    query = (
        update(Event)
        .where(Event.id == ticket.event_id)
        .where(Event.tickets_quantity > Event.tickets_sold)
        .values(tickets_sold=Event.tickets_sold + 1)
        .returning(Event)
    )
    result = await db.execute(query)
    event = result.scalar_one_or_none()

    if not event:
        check_query = select(Event.id).where(Event.id == ticket.event_id)
        check_result = await db.execute(check_query)
        event_exists = check_result.scalar_one_or_none()

        if not event_exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
            )

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Sold out. No ticket available"
        )

    new_ticket = Ticket(owner_id=user.id, **ticket.model_dump())

    db.add(new_ticket)
    try:
        await db.commit()
        await db.refresh(new_ticket)

        new_ticket.event_title = event.title

        logger.info(f"Ticket created {new_ticket.id}")
        return new_ticket
    except SQLAlchemyError as e:
        await db.rollback()

        logger.error(f"Database error occurred while creating ticket:{e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred while creating ticket",
        )


@router.get(
    "/{ticket_id}", response_model=TicketResponse, status_code=status.HTTP_200_OK
)
async def get_ticket(db: DBDep, ticket_id: int = 0):
    query = (
        select(Ticket)
        .options(selectinload(Ticket.event))
        .filter(Ticket.id == ticket_id)
    )
    result = await db.execute(query)
    ticket = result.scalars().first()
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found"
        )
    ticket.event_title = ticket.event.title
    return ticket


@router.get("/", response_model=list[TicketResponse], status_code=status.HTTP_200_OK)
async def get_tickets(
    db: DBDep, offset: int = 0, page_limit: int = settings.DEFAULT_PAGE_LIMIT
):
    query = (
        select(Ticket)
        .options(selectinload(Ticket.event))
        .offset(offset)
        .limit(page_limit)
    )
    result = await db.execute(query)
    tickets = result.scalars().all()

    for ticket in tickets:
        ticket.event_title = ticket.event.title

    return tickets


@router.delete("/{ticket_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ticket(ticket_id: int, db: DBDep):
    ticket = await db.get(Ticket, ticket_id)
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found"
        )

    try:
        await db.delete(ticket)
        await db.commit()

        logger.info(f"Ticket deleted {ticket_id}")
    except SQLAlchemyError as e:
        await db.rollback()

        logger.error(f"Database error occurred while deleting {ticket_id} ticket {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error while deleting ticket",
        )


@router.patch(
    "/{ticket_id}", response_model=TicketResponse, status_code=status.HTTP_200_OK
)
async def update_ticket(ticket_id: int, update_data: TicketUpdate, db: DBDep):
    query = (
        select(Ticket)
        .options(selectinload(Ticket.event))
        .filter(Ticket.id == ticket_id)
    )
    result = await db.execute(query)

    ticket = result.scalars().first()
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found"
        )

    update_dict = update_data.model_dump(exclude_unset=True)
    if not update_dict:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No field provided for update",
        )

    for key, value in update_dict.items():
        setattr(ticket, key, value)

    try:
        await db.commit()
        await db.refresh(ticket)

        ticket.event_title = ticket.event.title

        logger.info(f"Ticket updated {ticket_id}")
        return ticket
    except SQLAlchemyError as e:
        await db.rollback()

        logger.error(f"Database error occurred while updating {ticket_id} ticket {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error while updating ticket",
        )
