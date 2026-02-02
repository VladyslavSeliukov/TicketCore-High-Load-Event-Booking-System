from fastapi import APIRouter, status, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

from src.api.deps import DBDep
from src.core.config import settings
from src.core.logger import logger
from src.models import Event
from src.schemas.event import EventCreate, EventResponse, EventUpdate

router = APIRouter()

@router.post('/', response_model=EventResponse, status_code=status.HTTP_201_CREATED)
async def create_event(
        event: EventCreate,
        db: DBDep
):
    try:
        event_dict = event.model_dump()
        new_event = Event(**event_dict)
        db.add(new_event)
        await db.commit()

        await db.refresh(new_event)
        logger.info(f'Event created {new_event.id}')

        return new_event
    except SQLAlchemyError as e:
        await db.rollback()

        logger.error(f'Database error occurred while creating event: {e}')
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Database error while creating event'
        )

@router.get('/{event_id}', response_model=EventResponse, status_code=status.HTTP_200_OK)
async def get_event(
        db: DBDep,
        event_id: int = 0
):
    event = await db.get(Event, event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Event not found'
        )

    return event

@router.get('/', response_model=list[EventResponse], status_code=status.HTTP_200_OK)
async def get_events(
        db: DBDep,
        offset : int = 0,
        page_limit : int = settings.DEFAULT_PAGE_LIMIT
):
    query = (
        select(Event)
        .offset(offset)
        .limit(page_limit)
    )
    result = await db.execute(query)
    events = result.scalars().all()

    return events

@router.delete('/{event_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(
    event_id: int,
    db: DBDep
):
    event = await db.get(Event, event_id)
    if not event:
        raise HTTPException(
            status_code = status.HTTP_404_NOT_FOUND,
            detail='Event not found'
        )

    try:
        await db.delete(event)
        await db.commit()

        logger.info(f'Event deleted {event_id}')
    except IntegrityError as e:
        await db.rollback()

        logger.warning(f'User tried to delete the {event_id} event, but tickets for it already exist {e}')
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail='Cannot delete this event, because ticket for it already exist'
        )
    except SQLAlchemyError as e:
        await db.rollback()

        logger.error(f'Database error occurred while deleting event {event_id} event: {e}')
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Cannot delete this event'
        )

    return None

@router.put('/{event_id}', response_model=EventResponse, status_code=status.HTTP_200_OK)
async def update_event(
        db: DBDep,
        event_id: int,
        update_data: EventUpdate,
):
    event = await db.get(Event, event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Event not found'
        )

    update_data = update_data.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='No field provided for update'
        )

    for key, value in update_data.items():
        setattr(event, key, value)

    try:
        await db.commit()
        await db.refresh(event)

        logger.info(f'Event updated {event_id}')
        return event
    except SQLAlchemyError as e:
        await db.rollback()

        logger.error(f'Database error occurred while updating {event_id} event {e}')
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Database error while updating event'
        )