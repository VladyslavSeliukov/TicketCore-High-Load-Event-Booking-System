from collections.abc import AsyncGenerator, Awaitable, Callable, Generator
from typing import Any

from dotenv import load_dotenv

from src.models import Event, Ticket, User

load_dotenv()

import asyncio

import asyncpg
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import NullPool, select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.core.config import settings
from src.db.base import Base
from src.db.session import get_db
from src.main import app
from tests.factories import EventFactory, TicketFactory, UserFactory

TEST_DB_NAME = f"{settings.POSTGRES_DB}_test"
SYSTEM_URL = settings.DATABASE_URL.replace(f"/{settings.POSTGRES_DB}", "/postgres")
TEST_DB_URL = settings.DATABASE_URL.replace(
    f"/{settings.DATABASE_URL}", f"/{TEST_DB_NAME}"
)

test_engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
TestingSession = sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


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
    async with TestingSession() as session:
        await session.execute(
            text("TRUNCATE TABLE tickets, events, users RESTART IDENTITY CASCADE;")
        )
        await session.commit()


@pytest.fixture
async def db_connection() -> AsyncGenerator[AsyncSession, None]:
    async with TestingSession() as session:
        yield session


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with TestingSession() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="https://test"
    ) as c:
        yield c

    app.dependency_overrides.clear()


@pytest.fixture
async def event_factory(
    db_connection: AsyncSession,
) -> Callable[..., Awaitable[Event]]:
    async def _create(**kwargs: Any) -> Event:
        event = EventFactory.build(**kwargs)

        db_connection.add(event)
        await db_connection.commit()
        await db_connection.refresh(event)

        return event

    return _create


@pytest.fixture
async def ticket_factory(
    db_connection: AsyncSession,
) -> Callable[..., Awaitable[Ticket]]:
    async def _create(event_id: int, **kwargs: Any) -> Ticket:
        ticket = TicketFactory.build(event_id, **kwargs)

        db_connection.add(ticket)
        await db_connection.commit()
        await db_connection.refresh(ticket)

        return ticket

    return _create


@pytest.fixture
async def normal_user(db_connection: AsyncSession) -> User:
    user = UserFactory.build()

    db_connection.add(user)
    await db_connection.commit()
    await db_connection.refresh(user)

    return user


@pytest.fixture
async def superuser(db_connection: AsyncSession) -> User:
    superuser = UserFactory.build(is_superuser=True)

    db_connection.add(superuser)
    await db_connection.commit()
    await db_connection.refresh(superuser)

    return superuser


@pytest.fixture
async def user_token_headers(client: AsyncClient, normal_user: User) -> dict[str, str]:
    login_data = {"username": normal_user.email, "password": "very_secure_password"}

    response = await client.post("/api/v1/auth/login", data=login_data)
    assert response.status_code == 200
    token = response.json()["access_token"]

    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def superuser_token_headers(
    client: AsyncClient, superuser: User
) -> dict[str, str]:
    login_data = {"username": superuser.email, "password": "very_secure_password"}

    response = await client.post("/api/v1/auth/login", data=login_data)
    assert response.status_code == 200

    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def authorized_user(
    client: AsyncGenerator[AsyncClient, None], user_token_headers: dict[str, str]
) -> AsyncClient:
    client.headers.update(user_token_headers)
    return client


@pytest.fixture
async def authorized_superuser(
    client: AsyncGenerator[AsyncClient, None], superuser_token_headers: dict[str, str]
) -> AsyncClient:
    client.headers.update(superuser_token_headers)
    return client


@pytest.fixture
async def event_in_db(db_connection: AsyncSession) -> Event:
    existing_event = EventFactory.build()

    db_connection.add(existing_event)
    await db_connection.commit()
    await db_connection.refresh(existing_event)

    return existing_event


@pytest.fixture
async def get_event_by_id(
    db_connection: AsyncSession,
) -> Callable[[int], Awaitable[Event | None]]:
    async def _get_event(id: int) -> Event | None:
        query = select(Event).where(Event.id == id)
        result = await db_connection.execute(query)

        return result.scalar_one_or_none()

    return _get_event


@pytest.fixture
async def get_event_by_title(
    db_connection: AsyncSession,
) -> Callable[[str], Awaitable[Event | None]]:
    async def _get_event(title: str) -> Event | None:
        query = select(Event).where(Event.title == title)
        result = await db_connection.execute(query)

        return result.scalar_one_or_none()

    return _get_event


@pytest.fixture
async def user_in_db(db_connection: AsyncSession) -> User:
    user = UserFactory.build()

    db_connection.add(user)
    await db_connection.commit()
    await db_connection.refresh(user)

    return user
