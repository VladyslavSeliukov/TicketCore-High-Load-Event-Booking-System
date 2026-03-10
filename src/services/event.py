from collections.abc import Sequence

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core import logger
from src.core.exception import EventDeleteError, EventNotFoundError
from src.repositories.event import CachedEventRepository, EventRepository
from src.schemas import EventCreate, EventDetailResponse, EventResponse, EventUpdate


class EventService:
    """Service for managing event business logic and coordinating data access.

    Acts as an orchestrator between the base repository, caching proxy,
    and database transactions (commit/rollback) to maintain the Unit of Work.
    """

    def __init__(
        self,
        session: AsyncSession,
        base_repo: EventRepository,
        cached_repo: CachedEventRepository,
    ) -> None:
        self.db = session
        self.base_repo = base_repo
        self.cached_repo = cached_repo

    async def create(self, event_data: EventCreate) -> EventResponse:
        """Create a new event and invalidate related caches.

        Args:
            event_data (EventCreate): Schema containing the details of the event.

        Returns:
            EventResponse: DTO containing the newly created event details.

        Raises:
            SQLAlchemyError: If the database transaction fails.
        """
        try:
            new_event = await self.base_repo.create(event_data)
            await self.db.commit()

            await self.cached_repo.invalidate_event(new_event.id)
            logger.info(f"Event created {new_event.id}")
        except SQLAlchemyError:
            await self.db.rollback()
            raise

        return EventResponse.model_validate(new_event, from_attributes=True)

    async def get(self, event_id: int) -> EventDetailResponse:
        """Retrieve an event by its ID.

        Delegates the retrieval to the caching repository, which handles
        Redis cache hits/misses and database fallback.

        Args:
            event_id (int): The unique identifier of the event.

        Returns:
            EventDetailResponse: DTO containing event details.

        Raises:
            EventNotFoundError: If the event does not exist.
        """
        return await self.cached_repo.get(event_id)

    async def get_all(self, offset: int, limit: int) -> Sequence[EventResponse]:
        """Retrieve a paginated list of events.

        Delegates the retrieval to the caching repository to serve
        high-throughput read requests from Redis.

        Args:
            offset (int): Pagination offset.
            limit (int): Pagination limit.

        Returns:
            Sequence[EventResponse]: A list of validated event DTOs.
        """
        return await self.cached_repo.get_all(offset=offset, limit=limit)

    async def delete(self, event_id: int) -> None:
        """Delete an event and clear its associated caches.

        Args:
            event_id (int): The unique identifier of the event to delete.

        Raises:
            EventNotFoundError: If the event does not exist.
            EventDeleteError: If the event cannot be deleted due to existing tickets.
            SQLAlchemyError: If the database transaction fails.
        """
        event = await self.base_repo.get(event_id)

        if not event:
            raise EventNotFoundError("Event not found")

        try:
            await self.base_repo.delete(event)
            await self.db.commit()

            await self.cached_repo.invalidate_event(event_id)
            logger.info(f"Event deleted: {event_id}")
        except IntegrityError as e:
            await self.db.rollback()

            logger.warning(
                f"Attempt to delete event {event_id} failed: tickets already exist"
            )
            raise EventDeleteError("Cannot delete event with existing tickets") from e
        except SQLAlchemyError:
            await self.db.rollback()
            raise

    async def update(self, event_id: int, update_data: EventUpdate) -> EventResponse:
        """Update an existing event and proactively warm up the cache.

        Updates the database record, clears the old cache, and immediately
        fetches the updated data to warm up the cache for subsequent reads.

        Args:
            event_id (int): The unique identifier of the event.
            update_data (EventUpdate): Schema containing the fields to update.

        Returns:
            EventResponse: DTO containing the updated event details.

        Raises:
            EventNotFoundError: If the event does not exist.
            SQLAlchemyError: If the database transaction fails.
        """
        event = await self.base_repo.get(event_id)

        if not event:
            raise EventNotFoundError("Event not found")

        update_dict = update_data.model_dump(exclude_unset=True)
        if not update_dict:
            return EventResponse.model_validate(event)

        try:
            await self.base_repo.update(event, update_dict)
            await self.db.commit()

            await self.cached_repo.invalidate_event(event_id)
            logger.info(f"Event updated: {event_id}")

            return EventResponse.model_validate(event)
        except SQLAlchemyError:
            await self.db.rollback()
            raise
