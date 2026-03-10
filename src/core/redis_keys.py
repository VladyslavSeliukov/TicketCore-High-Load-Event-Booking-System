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
