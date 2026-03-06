from __future__ import annotations

from typing import TYPE_CHECKING, Any

from arq import ArqRedis
from arq.connections import RedisSettings, create_pool
from redis.asyncio import ConnectionPool, Redis

from src.core import settings

if TYPE_CHECKING:
    RedisPool = ConnectionPool[Any]
    RedisClient = Redis[Any]
else:
    RedisPool = ConnectionPool
    RedisClient = Redis

redis_pool: RedisPool | None = None
arq_pool: ArqRedis | None = None


async def init_redis_pool() -> None:
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
    global redis_pool

    if redis_pool:
        await redis_pool.disconnect()

    if arq_pool:
        await arq_pool.close()


async def get_redis() -> RedisClient:
    if not redis_pool:
        raise RuntimeError("Redis pool is not initialized")
    return Redis(connection_pool=redis_pool)


async def get_arq_pool() -> ArqRedis:
    if not arq_pool:
        raise RuntimeError("Arq pool is not initialized")
    return arq_pool
