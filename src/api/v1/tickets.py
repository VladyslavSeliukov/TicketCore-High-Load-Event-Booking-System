from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from src.core.config import settings
from src.db.session import get_db
from src.models import Event
from src.models.ticket import Ticket
from src.schemas.ticket import TicketCreate, TicketResponse
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

        logger.info(f'Ticket created {new_ticket.event_id}. Id {new_ticket.id}')

        return new_ticket
    except SQLAlchemyError as e:
        await db.rollback()

        logger.error(f'Database error occurred while creating ticket:{e}')
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Database error occurred while creating ticket'
        )

@router.get('/', response_model=list[TicketResponse])
async def get_tickets(
        offset: int = 0,
        page_limit: int = settings.DEFAULT_PAGE_LIMIT,
        db: AsyncSession = Depends(get_db)
):
    try:
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
    except Exception as e:
        logger.error(f'Database error occurred while getting tickets:{e}')
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Could not fetch tickets'
        )