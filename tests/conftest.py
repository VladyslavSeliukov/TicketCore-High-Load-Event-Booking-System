import asyncio

import asyncpg
import pytest
from dotenv import load_dotenv
from httpx import AsyncClient, ASGITransport
from sqlalchemy import text, NullPool
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from factories import UserFactory

load_dotenv()

from src.core.config import settings
from src.db.base import Base
from src.main import app
from src.db.session import get_db
from tests.factories import EventFactory, TicketFactory

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
        await session.execute(text('TRUNCATE TABLE tickets, events, users RESTART IDENTITY CASCADE;'))
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

@pytest.fixture
async def event_factory(db_connection):
    async def _create(**kwargs):
        event = EventFactory.build(**kwargs)

        db_connection.add(event)
        await db_connection.commit()
        await db_connection.refresh(event)

        return event
    return _create

@pytest.fixture
async def ticket_factory(db_connection):
    async def _create(event_id, price, **kwargs):
        ticket = TicketFactory.build(event_id, **kwargs)

        db_connection.add(ticket)
        await db_connection.commit()
        await db_connection.refresh(ticket)

        return ticket
    return _create

@pytest.fixture
async def normal_user(db_connection):
    user = UserFactory.build()

    db_connection.add(user)
    await db_connection.commit()
    await db_connection.refresh(user)

    return user

@pytest.fixture
async def superuser(db_connection):
    superuser  = UserFactory.build(is_superuser = True)

    db_connection.add(superuser)
    await db_connection.commit()
    await db_connection.refresh(superuser)

    return superuser

@pytest.fixture
async def user_token_headers(client, user):
    login_data = {
        'email' : user.email,
        'hashed_password' : 'very_secure_password'
    }

    response = await client.post('/api/v1/auth/login', data=login_data)
    assert response.status_code == 201
    token = response.json()['access']

    return {'Authorization' : f'Bearer {token}'}

@pytest.fixture
async def superuser_koken_headers(client, superuser):
    loging_data = {
        'username' : superuser.email,
        'password' : 'very_secure_password'
    }

    response = await client.post('/api/v1/auth/login/', data=loging_data)
    assert response.status_code == 201
    token = response.json()['access_token']

    return {'Authorization' : f'Bearer{token}'}

@pytest.fixture
async def authorized_client(client, user_token_headers):
    client.headers.update(user_token_headers)
    return client

@pytest.fixture
async def authorized_superuser(client, superuser_token_headers):
    client.headers.update(superuser_token_headers)
    return client