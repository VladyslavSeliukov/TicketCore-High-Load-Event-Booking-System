from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core import logger
from src.core.exception import (
    TicketTypeDeleteError,
    TicketTypeNotFoundError,
    TicketTypeQuantity,
)
from src.core.redis_keys import RedisClient, RedisKeys
from src.models import TicketType
from src.schemas.ticket_type import (
    TicketTypeCreate,
    TicketTypeDetailResponse,
    TicketTypeResponse,
    TicketTypeUpdate,
)


class TicketTypeService:
    """Service for managing ticket categories.

    Handles pricing, creation, and inventory limits for specific events.
    Responsible for proactive cache warming of the Redis inventory.
    """

    def __init__(self, session: AsyncSession, redis: RedisClient) -> None:
        self.db = session
        self.redis = redis

    async def create(
        self, event_id: int, type_data: TicketTypeCreate
    ) -> TicketTypeResponse:
        """Create a new ticket type and warm up the inventory cache.

        Args:
            event_id (int): The ID of the event this ticket type belongs to.
            type_data (TicketTypeCreate): Schema containing ticket type details.

        Returns:
            TicketTypeResponse: DTO containing the created ticket type.

        Raises:
            SQLAlchemyError: If the database transaction fails.
        """
        type_dict = type_data.model_dump()

        type_dict["event_id"] = event_id

        new_ticket_type = TicketType(**type_dict)
        self.db.add(new_ticket_type)

        try:
            await self.db.commit()
            await self.db.refresh(new_ticket_type)

            inventory_key = RedisKeys.ticket_type_inventory(new_ticket_type.id)
            await self.redis.set(inventory_key, new_ticket_type.tickets_quantity)

            await self.redis.delete(RedisKeys.event_static(event_id))
            await RedisKeys.bump_event_list_version(self.redis)

            logger.info(f"TicketType created: {new_ticket_type.id}")
        except SQLAlchemyError:
            await self.db.rollback()
            raise

        return TicketTypeResponse.model_validate(new_ticket_type, from_attributes=True)

    async def get(self, ticket_type_id: int) -> TicketTypeDetailResponse:
        """Retrieve a specific ticket type by its ID.

        Args:
            ticket_type_id (int): The unique identifier of the ticket type.

        Returns:
            TicketTypeDetailResponse: DTO containing the ticket type details.

        Raises:
            TicketTypeNotFoundError: If the ticket type does not exist.
        """
        ticket_type = await self.db.get(TicketType, ticket_type_id)
        if not ticket_type:
            raise TicketTypeNotFoundError("Ticket type not found")
        return TicketTypeDetailResponse.model_validate(
            ticket_type, from_attributes=True
        )

    async def get_all_for_event(
        self, event_id: int, offset: int, limit: int
    ) -> Sequence[TicketTypeResponse]:
        """Retrieve all ticket types associated with a specific event.

        Args:
            event_id (int): The ID of the target event.
            offset (int): Pagination offset.
            limit (int): Pagination limit.

        Returns:
            Sequence[TicketTypeResponse]: A list of ticket type DTOs.
        """
        query = (
            select(TicketType)
            .where(TicketType.event_id == event_id)
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.scalars(query)
        return [
            TicketTypeResponse.model_validate(tt, from_attributes=True)
            for tt in result.all()
        ]

    async def delete(self, ticket_type_id: int) -> None:
        """Remove a ticket type and invalidate related caches.

        Prevents deletion if there are already tickets sold or reserved for this type
        to maintain relational integrity.

        Args:
            ticket_type_id (int): The unique identifier of the ticket type to delete.

        Raises:
            TicketTypeNotFoundError: If the ticket type does not exist.
            TicketTypeDeleteError: If deletion violates foreign key constraints.
            SQLAlchemyError: If the database transaction fails.
        """
        ticket_type = await self.db.get(TicketType, ticket_type_id)

        if not ticket_type:
            raise TicketTypeNotFoundError("Ticket type not found")

        try:
            event_id = ticket_type.event_id

            await self.db.delete(ticket_type)
            await self.db.commit()

            await self.redis.delete(RedisKeys.ticket_type_inventory(ticket_type_id))
            await self.redis.delete(RedisKeys.event_static(event_id))
            await RedisKeys.bump_event_list_version(self.redis)

            logger.info(f"Ticket type deleted: {ticket_type_id}")
        except IntegrityError as e:
            await self.db.rollback()
            logger.warning(
                f"Attempt to delete ticket type {ticket_type_id} with existing tickets"
            )
            raise TicketTypeDeleteError(
                "Cannot delete ticket type with existing tickets"
            ) from e
        except SQLAlchemyError:
            await self.db.rollback()
            raise

    async def update(
        self, ticket_type_id: int, update_data: TicketTypeUpdate
    ) -> TicketTypeResponse:
        """Update specific fields of an existing ticket type.

        Validates that the new total ticket quantity is not strictly less than
        the number of tickets already sold. Syncs updated inventory to Redis.

        Args:
            ticket_type_id (int): The unique identifier of the ticket type.
            update_data (TicketTypeUpdate): Schema containing the fields to update.

        Returns:
            TicketTypeResponse: DTO containing the updated ticket type.

        Raises:
            TicketTypeNotFoundError: If the ticket type does not exist.
            TicketTypeQuantity: If the new quantity is less than `tickets_sold`.
            SQLAlchemyError: If the database transaction fails.
        """
        ticket_type = await self.db.get(TicketType, ticket_type_id)

        if not ticket_type:
            raise TicketTypeNotFoundError("Ticket type not found")

        update_dict = update_data.model_dump(exclude_unset=True)
        if not update_dict:
            return TicketTypeResponse.model_validate(ticket_type, from_attributes=True)

        new_quantity = update_dict.get("tickets_quantity")
        if new_quantity is not None and new_quantity < ticket_type.tickets_sold:
            raise TicketTypeQuantity(
                f"Cannot set tickets_quantity ({new_quantity}) "
                f"less than tickets_sold ({ticket_type.tickets_sold})"
            )

        for key, value in update_dict.items():
            setattr(ticket_type, key, value)

        try:
            await self.db.commit()
            await self.db.refresh(ticket_type)

            if new_quantity is not None:
                inventory_key = RedisKeys.ticket_type_inventory(ticket_type.id)
                available_tickets = (
                    ticket_type.tickets_quantity - ticket_type.tickets_sold
                )
                await self.redis.set(inventory_key, available_tickets)

            await self.redis.delete(RedisKeys.event_static(ticket_type.event_id))
            await RedisKeys.bump_event_list_version(self.redis)

            logger.info(f"Ticket type updated: {ticket_type_id}")
        except SQLAlchemyError:
            await self.db.rollback()
            raise

        return TicketTypeResponse.model_validate(ticket_type, from_attributes=True)
