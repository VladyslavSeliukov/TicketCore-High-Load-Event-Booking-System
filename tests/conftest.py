import asyncio

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from src.core.config import settings
from src.db.base import Base
from src.main import app

test_engine = create_async_engine(settings.DATABASE_URL)
TestingSession = sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

@pytest.fixture(scope='session')
def event_loop():
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope='session', autouse=True)
async def db_setup(event_loop):
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture(scope='session')
async def db_connection():
    async with TestingSession() as session:
        yield session
        await session.rollback()

@pytest.fixture(scope='session')
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url='https://test') as c:
        yield c