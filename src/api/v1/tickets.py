from fastapi import APIRouter, Depends, HTTPException, logger, status
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.core.config import settings
from src.db.session import get_db
from src.models.ticket import Ticket
from src.schemas.ticket import TicketCreate, TicketResponse

router = APIRouter()

@router.post('/', response_model=TicketResponse, status_code=201)
async def create_ticket(
        ticket: TicketCreate,
        db: AsyncSession = Depends(get_db)
):
    try:
        ticket_dict = ticket.model_dump()
        new_ticket = Ticket(**ticket_dict)

        db.add(new_ticket)
        await db.commit()

        await db.refresh(new_ticket)

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
        limit: int = settings.DEFAULT_PAGE_LIMIT,
        db: AsyncSession = Depends(get_db)
):
    try:

        query = select(Ticket).offset(offset).limit(limit)
        result = await db.execute(query)

        tickets = result.scalars().all()

        return tickets
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Could not fetch tickets'
        )