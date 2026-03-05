import asyncio
from collections.abc import AsyncGenerator, Generator
from pathlib import Path

import asyncpg
import pytest
from dotenv import load_dotenv
from httpx import ASGITransport, AsyncClient
from sqlalchemy import NullPool, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.db.redis import close_redis_pool, init_redis_pool
from src.db.session import get_db
from src.main import app

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")

from src.core.config import settings  # noqa: E402
from src.db.base import Base  # noqa: E402

load_dotenv()

TEST_DB_NAME = f"{settings.POSTGRES_DB}_test"
SYSTEM_URL = settings.DATABASE_URL.replace(f"/{settings.POSTGRES_DB}", "/postgres")
TEST_DB_URL = settings.DATABASE_URL.replace(
    f"/{settings.DATABASE_URL}", f"/{TEST_DB_NAME}"
)

test_engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
async_session_maker = async_sessionmaker(test_engine, expire_on_commit=False)


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
async def setup_test_db(
    event_loop: asyncio.AbstractEventLoop,
) -> AsyncGenerator[None, None]:
    sys_url_clean = SYSTEM_URL.replace("+asyncpg", "")

    conn = await asyncpg.connect(sys_url_clean)

    await conn.execute(
        f"""
        SELECT pg_terminate_backend(pg_stat_activity.pid)
        FROM pg_stat_activity
        WHERE pg_stat_activity.datname = '{TEST_DB_NAME}'
        AND pid <> pg_backend_pid();
    """
    )

    await conn.execute(f'DROP DATABASE IF EXISTS "{TEST_DB_NAME}"')
    await conn.execute(f'CREATE DATABASE "{TEST_DB_NAME}"')
    await conn.close()

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    try:
        conn = await asyncpg.connect(sys_url_clean)
        await conn.execute(f'DROP DATABASE IF EXISTS "{TEST_DB_NAME}"')
        await conn.close()
    except Exception as e:
        print(f"Warning during DB drop: {e}")


@pytest.fixture(autouse=True)
async def clean_tables() -> None:
    async with async_session_maker() as session:
        await session.execute(
            text("TRUNCATE TABLE tickets, events, users RESTART IDENTITY CASCADE;")
        )
        await session.commit()


@pytest.fixture
async def db_connection() -> AsyncGenerator[AsyncSession, None]:
    connection = await test_engine.connect()
    transaction = await connection.begin()

    session = AsyncSession(bind=connection, expire_on_commit=False)

    yield session

    await session.close()
    await transaction.rollback()
    await connection.close()


@pytest.fixture(autouse=True)
async def setup_redis_for_tests() -> AsyncGenerator[None, None]:
    await init_redis_pool()
    yield
    await close_redis_pool()


@pytest.fixture
async def client(db_connection: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_connection

    app.dependency_overrides[get_db] = override_get_db

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="https://test"
        ) as c:
            yield c
    finally:
        app.dependency_overrides.pop(get_db, None)
