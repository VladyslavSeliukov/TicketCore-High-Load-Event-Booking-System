from collections.abc import Sequence

from arq import ArqRedis
from redis.asyncio import Redis
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core import logger, settings
from src.core.exception import (
    TicketNotFoundError,
    TicketsSoldOutError,
    TicketTypeNotFoundError,
)
from src.core.redis_keys import RedisKeys
from src.models import Ticket, TicketType
from src.schemas import TicketCreate, TicketResponse
from src.schemas.ticket import TicketDetailResponse

RedisClient = Redis


class TicketService:
    """Service for handling ticket reservations.

    Manages atomic ticket retrievals and inventory state via Redis Gatekeeper.
    Prevents race conditions using Lua scripts for inventory decrement.
    """

    def __init__(
        self, session: AsyncSession, arq_pool: ArqRedis, redis: RedisClient
    ) -> None:
        self.db = session
        self.arq_pool = arq_pool
        self.redis = redis

    async def create(self, user_id: int, ticket_data: TicketCreate) -> TicketResponse:
        """Reserve a ticket for a user atomically.

        Executes a Lua script in Redis to decrement available inventory. Implements
        fallback cache warming if the inventory key is missing. Enqueues a background
        task to release the ticket if unpaid within the reservation window.

        Args:
            user_id (int): The ID of the user making the purchase.
            ticket_data (TicketCreate): Schema containing the target ticket type ID.

        Returns:
            TicketResponse: DTO containing the newly created ticket.

        Raises:
            TicketTypeNotFoundError: If the ticket type does not exist during fallback.
            TicketsSoldOutError: If the Redis inventory counter reaches zero.
            SQLAlchemyError: Propagated if the database transaction fails.
        """
        inventory_key = RedisKeys.ticket_type_inventory(ticket_data.ticket_type_id)

        reserve_script = """
        local current = redis.call('GET', KEYS[1])
        if current == false then
            return -1
        end
        if tonumber(current) > 0 then
            redis.call('DECR', KEYS[1])
            return 1
        else
            return 0
        end
        """

        result = await self.redis.eval(reserve_script, 1, inventory_key)  # type: ignore[misc]

        if result == -1:
            ticket_type = await self.db.get(TicketType, ticket_data.ticket_type_id)
            if not ticket_type:
                raise TicketTypeNotFoundError("Ticket type not found")

            available_tickets = ticket_type.tickets_quantity - ticket_type.tickets_sold
            await self.redis.set(inventory_key, available_tickets)

            result = await self.redis.eval(reserve_script, 1, inventory_key)  # type: ignore[misc]

        if result == 0:
            raise TicketsSoldOutError("Sold out. No tickets of this type available")

        try:
            update_query = (
                update(TicketType)
                .where(TicketType.id == ticket_data.ticket_type_id)
                .values(tickets_sold=TicketType.tickets_sold + 1)
            )
            await self.db.execute(update_query)

            new_ticket = Ticket(owner_id=user_id, **ticket_data.model_dump())
            self.db.add(new_ticket)

            await self.db.commit()
            await self.db.refresh(new_ticket)

            logger.info(f"Ticket created: {new_ticket.id}")

            await self.arq_pool.enqueue_job(
                "release_unpaid_ticket",
                new_ticket.id,
                _defer_by=settings.TICKET_RESERVATION_TIME_SECONDS,
            )
        except IntegrityError as e:
            await self.db.rollback()
            await self.redis.incr(inventory_key)

            error_msg = str(e).lower()
            if (
                "ck_ticket_types_check_sold_limit" in error_msg
                or "checkviolation" in error_msg
            ):
                raise TicketsSoldOutError(
                    "Sold out. No tickets of this type available"
                ) from e
            raise
        except SQLAlchemyError:
            await self.db.rollback()
            await self.redis.incr(inventory_key)
            raise

        return TicketResponse.model_validate(new_ticket, from_attributes=True)

    async def get(self, owner_id: int, ticket_id: int) -> TicketDetailResponse:
        """Retrieve a specific ticket belonging to a user.

        Args:
            owner_id (int): The ID of the user requesting the ticket.
            ticket_id (int): The unique identifier of the ticket.

        Returns:
            TicketDetailResponse: ticket details and related event/type data (DTO).

        Raises:
            TicketNotFoundError: If the ticket doesn't exist/does not belong to the user
        """
        query = (
            select(Ticket)
            .options(selectinload(Ticket.ticket_type).joinedload(TicketType.event))
            .where(Ticket.id == ticket_id)
            .where(Ticket.owner_id == owner_id)
        )
        ticket = await self.db.scalar(query)
        if not ticket:
            raise TicketNotFoundError("Ticket not found")

        return TicketDetailResponse.model_validate(ticket, from_attributes=True)

    async def get_all_for_user(
        self, owner_id: int, offset: int, limit: int
    ) -> Sequence[TicketResponse]:
        """Retrieve a paginated list of tickets owned by a specific user.

        Args:
            owner_id (int): The ID of the user.
            offset (int): Pagination offset.
            limit (int): Pagination limit.

        Returns:
            Sequence[TicketResponse]: A list of ticket DTOs.
        """
        query = (
            select(Ticket)
            .where(Ticket.owner_id == owner_id)
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.scalars(query)
        return [
            TicketResponse.model_validate(t, from_attributes=True) for t in result.all()
        ]

    async def delete(self, owner_id: int, ticket_id: int) -> None:
        """Cancel a ticket reservation and atomically restore inventory.

        Deletes the ticket from PostgreSQL and safely increments the inventory
        counter in Redis using a Lua script to avoid creating ghost inventory.

        Args:
            owner_id (int): The ID of the ticket owner.
            ticket_id (int): The unique identifier of the ticket to delete.

        Raises:
            TicketNotFoundError: If the ticket is not found or unauthorized.
            SQLAlchemyError: If the database transaction fails.
        """
        query = (
            select(Ticket)
            .where(Ticket.id == ticket_id)
            .where(Ticket.owner_id == owner_id)
        )
        ticket = await self.db.scalar(query)

        if not ticket:
            raise TicketNotFoundError("Ticket not found")
        try:
            update_query = (
                update(TicketType)
                .where(TicketType.id == ticket.ticket_type_id)
                .values(tickets_sold=TicketType.tickets_sold - 1)
            )
            await self.db.execute(update_query)

            await self.db.delete(ticket)
            await self.db.commit()

            safe_incr_script = """
            if redis.call('EXISTS', KEYS[1]) == 1 then
                redis.call('INCR', KEYS[1])
            end
            """
            inventory_key = RedisKeys.ticket_type_inventory(ticket.ticket_type_id)
            await self.redis.eval(safe_incr_script, 1, inventory_key)  # type: ignore[misc]

            logger.info(f"Ticket deleted: {ticket_id}")
        except SQLAlchemyError:
            await self.db.rollback()
            raise
