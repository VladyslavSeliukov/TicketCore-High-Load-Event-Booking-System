import asyncio
import asyncpg
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import text, NullPool
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from src.core.config import settings
from src.db.base import Base
from src.main import app
from src.db.session import get_db

TEST_DB_NAME = f'{settings.POSTGRES_DB}_test'
SYSTEM_URL = settings.DATABASE_URL.replace(f'/{settings.POSTGRES_DB}', '/postgres')
TEST_DB_URL = settings.DATABASE_URL.replace(f'/{settings.DATABASE_URL}', f'/{TEST_DB_NAME}')

test_engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
TestingSession = sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

@pytest.fixture(scope='session')
def event_loop():
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope='session', autouse=True)
async def setup_test_db(event_loop):
    sys_url_clean = SYSTEM_URL.replace('+asyncpg', '')

    conn = await asyncpg.connect(sys_url_clean)

    await conn.execute(f"""
        SELECT pg_terminate_backend(pg_stat_activity.pid)
        FROM pg_stat_activity
        WHERE pg_stat_activity.datname = '{TEST_DB_NAME}'
        AND pid <> pg_backend_pid();
    """)

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
        print(f'Warning during DB drop: {e}')

@pytest.fixture(autouse=True)
async def clean_tables():
    async with TestingSession() as session:
        await session.execute(text('TRUNCATE TABLE tickets, events RESTART IDENTITY CASCADE;'))
        await session.commit()

@pytest.fixture
async def db_connection():
    async with TestingSession() as session:
        yield session

@pytest.fixture
async def client():
    async def override_get_db():
        async with TestingSession() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url='https://test') as c:
        yield c

    app.dependency_overrides.clear()