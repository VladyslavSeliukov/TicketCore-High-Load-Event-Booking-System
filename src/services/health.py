from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core import logger
from src.core.exception import HealthError


class HealthService:
    """Service for checking critical infrastructure availability."""

    def __init__(self, session: AsyncSession, redis: Redis) -> None:
        self.db = session
        self.redis = redis

    async def check_readiness(self) -> bool:
        """Ping all critical dependencies.

        Executes lightweight queries to verify active connections to essential
        backing services like PostgreSQL and Redis.

        Raises:
            HealthError: If any of the database or cache connections fail.
        """
        try:
            await self.db.execute(text("SELECT 1"))
            await self.redis.ping()
            return True
        except Exception as e:
            logger.info(f"Readiness check failed: {e}")
            raise HealthError("Service Dependencies Unavailable") from e
