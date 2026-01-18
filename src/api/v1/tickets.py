from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from src.schemas.ticket import TicketCreate, TicketResponse
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

@router.put('/', status_code=status.HTTP_200_OK)
async def update_ticket(

):
    pass