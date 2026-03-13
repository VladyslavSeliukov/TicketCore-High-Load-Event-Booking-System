from collections.abc import Awaitable
from typing import cast

from redis.asyncio import Redis

RedisClient = Redis


class RedisKeys:
    """Centralized Key Registry for Redis caching and inventory management.

    Ensures strict key naming conventions, prevents collisions, and provides
    methods for O(1) cache invalidation via versioning.
    """

    TTL_STATIC_24H: int = 86400
    TTL_LISTS_1H: int = 3600

    @staticmethod
    def event_static(event_id: int) -> str:
        """Generate a cache key for static event data.

        Args:
            event_id (int): The unique identifier of the event.

        Returns:
            str: Formatted Redis key string.
        """
        return f"ticketcore:events:static:{event_id}"

    @staticmethod
    def ticket_type_inventory(ticket_type_id: int) -> str:
        """Generate a key for the atomic ticket inventory counter.

        Used by Lua scripts to prevent race conditions during ticket sales.

        Args:
            ticket_type_id (int): The unique identifier of the ticket type.

        Returns:
            str: Formatted Redis key string.
        """
        return f"ticketcore:inventory:ticket_type:{ticket_type_id}"

    @staticmethod
    async def event_list(redis: RedisClient, offset: int, limit: int) -> str:
        """Generate a versioned key for paginated event lists.

        Retrieves the current global cache version to allow O(1) bulk invalidation.

        Args:
            redis (RedisClient): Async Redis client instance.
            offset (int): Pagination offset.
            limit (int): Pagination limit.

        Returns:
            str: Formatted and versioned Redis key string.
        """
        version_val = await redis.get("ticketcore:events:list_version")

        if not version_val:
            version = 1
            await redis.set("ticketcore:events:list_version", version)

        else:
            version = int(version_val)

        return f"ticketcore:events:list:v:{version}:o:{offset}:l:{limit}"

    @staticmethod
    async def bump_event_list_version(redis: RedisClient) -> None:
        """Perform an O(1) invalidation of all paginated event lists.

        Increments the global list version. Old keys will be naturally
        garbage collected by their TTL.

        Args:
            redis (RedisClient): Async Redis client instance.
        """
        await redis.incr("ticketcore:events:list_version")

    @staticmethod
    def canceled_tickets_set() -> str:
        """Generate the key for the Set of processed canceled tickets.

        Used to guarantee idempotency during inventory restoration. It stores
        the IDs of tickets that have already had their inventory successfully
        returned to the available pool.

        Returns:
            str: Formatted Redis key string.
        """
        return "system:canceled_tickets"

    @staticmethod
    def active_reservations_hash() -> str:
        """Generate the key for the Hash storing active ticket reservations.

        Maps ticket_id -> ticket_type_id. Used by the Garbage Collector
        to track locks and find 'ghost' reservations.
        """
        return "system:active_reservations"

    @classmethod
    async def refund_inventory_idempotent(
        cls, redis: Redis, ticket_type_id: int, ticket_id: int
    ) -> None:
        """Idempotently restore a canceled ticket's inventory slot.

        Executes an atomic Lua script to prevent the dual-write problem during
        background worker retries. It verifies if the ticket was already refunded
        by checking the processed set. If not, it registers the ticket and
        increments the available inventory.

        Args:
            redis: Async Redis client instance for the business logic database.
            ticket_type_id: The unique identifier of the ticket type to refund.
            ticket_id: The unique identifier of the canceled ticket.
        """
        lua_script = """
            -- KEYS[1] = inventory_key
            -- KEYS[2] = processed_tickets_set
            -- KEYS[3] = active_reservations_hash
            -- ARGV[1] = ticket_id

            if redis.call('SISMEMBER', KEYS[2], ARGV[1]) == 0 then
                redis.call('SADD', KEYS[2], ARGV[1])
                if redis.call('EXISTS', KEYS[1]) == 1 then
                    redis.call('INCR', KEYS[1])
                end
                redis.call('HDEL', KEYS[3], ARGV[1])
                return 1
            end
            return 0
            """
        inventory_key = cls.ticket_type_inventory(ticket_type_id)
        processed_set_key = cls.canceled_tickets_set()
        active_hash_key = cls.active_reservations_hash()

        await redis.eval(
            lua_script,
            3,
            inventory_key,
            processed_set_key,
            active_hash_key,
            str(ticket_id),
        )  # type: ignore[misc]

    @classmethod
    async def get_all_active_reservations(cls, redis: Redis) -> list[dict[str, int]]:
        """Fetch all currently active locks from Redis.

        Returns:
            A list of dicts: [{'ticket_id': 1, 'ticket_type_id': 2}, ...]
        """
        hash_key = cls.active_reservations_hash()
        raw_data = await cast(Awaitable[dict[bytes, bytes]], redis.hgetall(hash_key))

        reservations = []
        for ticket_id_bytes, val_bytes in raw_data.items():
            val_str = (
                val_bytes.decode("utf-8") if isinstance(val_bytes, bytes) else val_bytes
            )
            ticket_type_id_str, ts_str = val_str.split(":")

            reservations.append(
                {
                    "ticket_id": int(ticket_id_bytes),
                    "ticket_type_id": int(ticket_type_id_str),
                    "timestamp": int(ts_str),
                }
            )

        return reservations
