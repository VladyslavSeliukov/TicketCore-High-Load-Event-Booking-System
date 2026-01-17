from fastapi import APIRouter, status, HTTPException, Depends
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import select

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.logger import logger
from src.db.session import get_db
from src.models.event import Event
from src.schemas.event import EventCreate, EventResponse

router = APIRouter()

@router.post('/', response_model=EventResponse, status_code=status.HTTP_201_CREATED)
async def create_event(
        event : EventCreate,
        db : AsyncSession = Depends(get_db)
):
    try:
        event_dict = event.model_dump()
        new_event = Event(**event_dict)

        db.add(new_event)
        await db.commit()

        await db.refresh(new_event)
        logger.info(f'Event created {new_event.title}. Id {new_event.id}')

        return new_event
    except SQLAlchemyError as e:
        await db.rollback()

        logger.error(f'Database error occurred while creating an event: {e}')
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Database error while creating event'
        )

@router.get('/', response_model=list[EventResponse])
async def get_events(
        offset: int = 0,
        page_limit: int = settings.DEFAULT_PAGE_LIMIT,
        db : AsyncSession = Depends(get_db)
):
    try:
        query = select(Event).offset(offset).limit(page_limit)
        result = await db.execute(query)
        events = result.scalars().all()

        return events
    except Exception as e:
        logger.error(f'Database error occurred while getting events:{e}')

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Database error occurred while getting events'
        )