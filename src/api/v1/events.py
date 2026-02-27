from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from src.api.deps import DBDep, get_current_superuser
from src.core.config import settings
from src.core.logger import logger
from src.models import Event, User
from src.schemas.event import EventCreate, EventResponse, EventUpdate

router = APIRouter()


@router.post("/", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
async def create_event(
    event: EventCreate,
    db: DBDep,
    admin_user: Annotated[User, Depends(get_current_superuser)],
) -> Event:
    try:
        event_dict = event.model_dump()
        new_event = Event(**event_dict)
        db.add(new_event)
        await db.commit()

        await db.refresh(new_event)
        logger.info(f"Event created {new_event.id}")

        return new_event
    except SQLAlchemyError as e:
        await db.rollback()

        logger.error(f"Database error occurred while creating event: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error while creating event",
        ) from e


@router.get("/{event_id}", response_model=EventResponse, status_code=status.HTTP_200_OK)
async def get_event(db: DBDep, event_id: int = 0) -> Event:
    event = await db.get(Event, event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
        )

    return event


@router.get("/", response_model=list[EventResponse], status_code=status.HTTP_200_OK)
async def get_events(
    db: DBDep, offset: int = 0, limit: int = settings.DEFAULT_PAGE_LIMIT
) -> Sequence[Event]:
    query = select(Event).offset(offset).limit(limit)
    result = await db.execute(query)
    events = result.scalars().all()

    return events


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(
    event_id: int,
    db: DBDep,
    admin_user: Annotated[User, Depends(get_current_superuser)],
) -> None:
    event = await db.get(Event, event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
        )

    try:
        await db.delete(event)
        await db.commit()

        logger.info(f"Event deleted {event_id}")
    except IntegrityError as e:
        await db.rollback()

        logger.warning(
            f"User tried to delete the {event_id} event, "
            f"but tickets for it already exist {e}"
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete this event, because ticket for it already exist",
        ) from e
    except SQLAlchemyError as e:
        await db.rollback()

        logger.error(
            f"Database error occurred while deleting event {event_id} event: {e}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Cannot delete this event",
        ) from e

    return None


@router.patch(
    "/{event_id}", response_model=EventResponse, status_code=status.HTTP_200_OK
)
async def update_event(
    db: DBDep,
    event_id: int,
    update_data: EventUpdate,
    admin_user: Annotated[User, Depends(get_current_superuser)],
) -> Event:
    event = await db.get(Event, event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
        )

    update_dict = update_data.model_dump(exclude_unset=True)
    if not update_dict:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No field provided for update",
        )

    for key, value in update_dict.items():
        setattr(event, key, value)

    try:
        await db.commit()
        await db.refresh(event)

        logger.info(f"Event updated {event_id}")
        return event
    except SQLAlchemyError as e:
        await db.rollback()

        logger.error(f"Database error occurred while updating {event_id} event {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error while updating event",
        ) from e
