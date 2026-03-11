from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.core.config import settings

engine: AsyncEngine = create_async_engine(
    str(settings.DATABASE_URL),
    pool_size=50,
    max_overflow=100,
    pool_timeout=30.0,
    pool_pre_ping=True,
    echo=settings.ENVIRONMENT == "dev",
)

AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Provide a scoped asynchronous database session for FastAPI endpoints.

    Yields a new session per request. Automatically rolls back transactions
    if an unhandled exception occurs during the request lifecycle,
    and ensures the session is always closed afterward.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
