from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from src.schemas.ticket import TicketCreate, TicketResponse, TicketUpdate
from src.core.config import settings
from src.db.session import get_db
from src.models import Event
from src.models.ticket import Ticket
from src.core.logger import logger

router = APIRouter()

@router.post('/', response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
async def create_ticket(
        ticket: TicketCreate,
        db: AsyncSession = Depends(get_db)
):
    event = await db.get(Event, ticket.event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Event not found'
        )

    try:
        ticket_dict = ticket.model_dump()
        new_ticket = Ticket(**ticket_dict)
        db.add(new_ticket)
        await db.commit()

        await db.refresh(new_ticket)
        new_ticket.event_title = event.title
        logger.info(f'Ticket created {new_ticket.id}')

        return new_ticket
    except SQLAlchemyError as e:
        await db.rollback()

        logger.error(f'Database error occurred while creating ticket:{e}')
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Database error occurred while creating ticket'
        )

@router.get('/', response_model=list[TicketResponse], status_code=status.HTTP_200_OK)
async def get_tickets(
        offset: int = 0,
        page_limit: int = settings.DEFAULT_PAGE_LIMIT,
        db: AsyncSession = Depends(get_db)
):
    query = (
        select(Ticket)
        .options(joinedload(Ticket.event))
        .offset(offset)
        .limit(page_limit))
    result = await db.execute(query)
    tickets = result.scalars().all()

    for ticket in tickets:
        ticket.event_title = ticket.event.title

    return tickets

@router.delete('/{ticket_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_ticket(
    ticket_id: int,
    db: AsyncSession = Depends(get_db)
):
    ticket = await db.get(Ticket, ticket_id)
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Ticket not found'
        )

    try:
        await db.delete(ticket)
        await db.commit()

        logger.info(f'Ticket deleted {ticket_id}')
    except SQLAlchemyError as e:
        await db.rollback()

        logger.error(f'Database error occurred while deleting {ticket_id} ticket {e}')
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Database error while deleting ticket'
        )

@router.put('/{ticket_id}', response_model=TicketResponse, status_code=status.HTTP_200_OK)
async def update_ticket(
    ticket_id: int,
    update_data:  TicketUpdate,
    db: AsyncSession = Depends(get_db)
):
    query = (
        select(Ticket)
        .options(joinedload(Ticket.event))
        .filter(Ticket.id == ticket_id)
    )
    result = await db.execute(query)

    ticket = result.scalars().first()
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Ticket not found'
        )

    update_dict = update_data.model_dump(exclude_unset=True)
    if not update_dict:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='No field provided for update'
        )

    for key, value in update_dict.items():
        setattr(ticket, key, value)

    try:
        await db.commit()
        await db.refresh(ticket)

        ticket.event_title = ticket.event.title

        logger.info(f'Ticket updated {ticket_id}')
        return ticket
    except SQLAlchemyError as e:
        await db.rollback()

        logger.error(f'Database error occurred while updating {ticket_id} ticket {e}')
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Database error while updating ticket'
        )