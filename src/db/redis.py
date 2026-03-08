from __future__ import annotations

from arq import ArqRedis
from arq.connections import RedisSettings, create_pool
from redis.asyncio import ConnectionPool, Redis

from src.core import settings

RedisPool = ConnectionPool
RedisClient = Redis

redis_pool: RedisPool | None = None
arq_pool: ArqRedis | None = None


async def init_redis_pool() -> None:
    """Initialize global Redis connection pools on application startup.

    Creates separate async pools for general caching (RedisClient)
    and background task queuing (ArqRedis) to prevent resource starvation.
    """
    global redis_pool, arq_pool

    redis_pool = ConnectionPool.from_url(
        settings.REDIS_URL,
        decode_responses=True,
        max_connections=1000,
    )

    arq_pool = await create_pool(
        RedisSettings(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            database=1,
        )
    )


async def close_redis_pool() -> None:
    """Gracefully close all global Redis connections on application shutdown."""
    global redis_pool

    if redis_pool:
        await redis_pool.disconnect()

    if arq_pool:
        await arq_pool.aclose()


async def get_redis() -> RedisClient:
    """Dependency provider for the general-purpose Redis client."""
    if not redis_pool:
        raise RuntimeError("Redis pool is not initialized")
    return Redis(connection_pool=redis_pool)


async def get_arq_pool() -> ArqRedis:
    """Dependency provider for the ARQ background task broker."""
    if not arq_pool:
        raise RuntimeError("Arq pool is not initialized")
    return arq_pool
