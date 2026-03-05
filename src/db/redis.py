from __future__ import annotations

from typing import TYPE_CHECKING, Any

from redis.asyncio import ConnectionPool, Redis

from src.core import settings

if TYPE_CHECKING:
    RedisPool = ConnectionPool[Any]
    RedisClient = Redis[Any]
else:
    RedisPool = ConnectionPool
    RedisClient = Redis

redis_pool: RedisPool | None = None


async def init_redis_pool() -> None:
    global redis_pool

    redis_pool = ConnectionPool.from_url(
        settings.REDIS_URL,
        decode_responses=True,
        max_connections=1000,
    )


async def close_redis_pool() -> None:
    global redis_pool

    if redis_pool:
        await redis_pool.disconnect()


async def get_redis() -> RedisClient:
    if not redis_pool:
        raise RuntimeError("Redis pool is not initialized")
    return Redis(connection_pool=redis_pool)
