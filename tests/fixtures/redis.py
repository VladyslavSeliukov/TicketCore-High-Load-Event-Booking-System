from collections.abc import AsyncGenerator

import pytest
from redis.asyncio import Redis

from src.core.config import settings
from src.db.redis import close_redis_pool, init_redis_pool


@pytest.fixture()
async def setup_redis_for_tests() -> AsyncGenerator[None, None]:
    await init_redis_pool()
    yield
    await close_redis_pool()


@pytest.fixture()
async def flush_redis_between_tests() -> None:
    redis_client = Redis.from_url(settings.REDIS_URL)
    await redis_client.flushdb()
    await redis_client.aclose()
