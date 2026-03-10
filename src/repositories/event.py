from collections.abc import Sequence
from typing import Any

from pydantic import TypeAdapter
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.exception import EventDeleteError, EventNotFoundError
from src.core.redis_keys import RedisKeys
from src.models import Event
from src.schemas import EventCreate, EventDetailResponse, EventResponse

RedisClient = Redis


class EventRepository:
    """Repository for managing Event entities in PostgreSQL.

    Handles raw database operations without any caching logic.
    Provides methods for CRUD operations directly linked to SQLAlchemy sessions.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.db = session

    async def create(self, event_data: EventCreate) -> Event:
        """Create a new event in the database.

        Args:
            event_data (EventCreate): The schema containing the event details.

        Returns:
            Event: The newly created SQLAlchemy Event model instance.
        """
        new_event = Event(**event_data.model_dump())

        self.db.add(new_event)
        await self.db.flush()
        await self.db.refresh(new_event)

        return new_event

    async def get(self, event_id: int) -> Event | None:
        """Retrieve an event by its ID.

        Eagerly loads associated ticket types to avoid DetachedInstanceError.

        Args:
            event_id (int): The unique identifier of the event.

        Returns:
            Event | None: The event instance if found, otherwise None.
        """
        query = (
            select(Event)
            .options(selectinload(Event.ticket_types))
            .where(Event.id == event_id)
        )
        return await self.db.scalar(query)  # type: ignore[no-any-return]

    async def get_all(self, offset: int, limit: int) -> Sequence[Event]:
        """Retrieve a paginated list of events.

        Eagerly loads associated ticket types.

        Args:
            offset (int): The number of records to skip.
            limit (int): The maximum number of records to return.

        Returns:
            Sequence[Event]: A sequence of retrieved Event instances.
        """
        query = select(Event).offset(offset).limit(limit)
        result = await self.db.scalars(query)
        return result.all()

    async def delete(self, event: Event) -> None:
        """Delete an event from the database.

        Args:
            event (Event): The event model instance to delete.

        Raises:
            EventDeleteError: If the event cannot be deleted due to existing
                relational constraints (e.g., tickets are already sold).
        """
        try:
            await self.db.delete(event)
            await self.db.flush()
        except IntegrityError as e:
            raise EventDeleteError("Cannot delete event with existing tickets") from e

    async def update(self, event: Event, update_dict: dict[str, Any]) -> Event:
        """Update specific attributes of an existing event.

        Args:
            event (Event): The event model instance to update.
            update_dict (dict[str, Any]): A dictionary containing the fields to update.

        Returns:
            Event: The updated event instance with refreshed relationships.
        """
        for key, value in update_dict.items():
            setattr(event, key, value)
        await self.db.flush()
        await self.db.refresh(event, attribute_names=["ticket_types"])
        return event


class CachedEventRepository:
    """Proxy repository that wraps EventRepository with a Redis caching layer.

    Implements a Read-Aside caching strategy and provides methods for cache
    invalidation to maintain synchronization between PostgreSQL and Redis.
    """

    def __init__(self, repository: EventRepository, redis: RedisClient) -> None:
        self.repo = repository
        self.redis = redis

    async def get(self, event_id: int) -> EventDetailResponse:
        """Retrieve event details from cache or database.

        Checks Redis first. On a cache miss, fetches from the database, maps the
        ORM model to a DTO, caches the result for 24 hours, and returns it.

        Args:
            event_id (int): The unique identifier of the event.

        Returns:
            EventDetailResponse: The validated DTO containing event details.

        Raises:
            EventNotFoundError: If the event does not exist in the database.
        """
        cached_key = RedisKeys.event_static(event_id)

        cached_data = await self.redis.get(cached_key)
        if cached_data:
            return EventDetailResponse.model_validate_json(cached_data)

        event = await self.repo.get(event_id)
        if not event:
            raise EventNotFoundError("Event not found")

        event_dto = EventDetailResponse.model_validate(event)

        await self.redis.set(
            cached_key, event_dto.model_dump_json(), ex=RedisKeys.TTL_STATIC_24H
        )

        return event_dto

    async def get_all(self, offset: int, limit: int) -> Sequence[EventResponse]:
        """Retrieve a paginated list of events from cache or database.

        Uses versioned cache keys to fetch paginated lists. Caches the result
        for 1 hour on a cache miss.

        Args:
            offset (int): The number of records to skip.
            limit (int): The maximum number of records to return.

        Returns:
            Sequence[EventResponse]: A list of validated event DTOs.
        """
        cached_key = await RedisKeys.event_list(self.redis, offset, limit)
        cached_data = await self.redis.get(cached_key)

        adapter = TypeAdapter(list[EventResponse])

        if cached_data:
            return adapter.validate_json(cached_data)

        events = await self.repo.get_all(offset, limit)
        events_dto = [EventResponse.model_validate(e) for e in events]

        await self.redis.set(
            cached_key, adapter.dump_json(events_dto), ex=RedisKeys.TTL_LISTS_1H
        )

        return events_dto

    async def invalidate_event(self, event_id: int) -> None:
        """Clear cached data associated with a specific event.

        Deletes the static event cache and bumps the global list version to
        perform an O(1) invalidation of all paginated event lists.

        Args:
            event_id (int): The unique identifier of the event to invalidate.
        """
        await self.redis.delete(RedisKeys.event_static(event_id))
        await RedisKeys.bump_event_list_version(self.redis)
