import asyncio
from collections.abc import AsyncGenerator, Awaitable, Callable, Generator
from pathlib import Path
from typing import Any, cast

import asyncpg
import pytest
from dotenv import load_dotenv
from httpx import ASGITransport, AsyncClient
from sqlalchemy import NullPool, delete, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")

from src.api.deps import get_current_user  # noqa: E402
from src.core.config import settings  # noqa: E402
from src.db.base import Base  # noqa: E402
from src.db.session import get_db  # noqa: E402
from src.main import app  # noqa: E402
from src.models import Event, Ticket, TicketType, User  # noqa: E402
from tests.factories import (  # noqa: E402
    EventFactory,
    TicketFactory,
    TicketTypeFactory,
    UserFactory,
)

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
    client: AsyncClient, user_token_headers: dict[str, str]
) -> AsyncClient:
    client.headers.update(user_token_headers)
    return client


@pytest.fixture
async def authorized_superuser(
    client: AsyncClient, superuser_token_headers: dict[str, str]
) -> AsyncClient:
    client.headers.update(superuser_token_headers)
    return client


@pytest.fixture
async def user_in_db(db_connection: AsyncSession) -> User:
    user = UserFactory.build()

    db_connection.add(user)
    await db_connection.commit()
    await db_connection.refresh(user)

    return user


@pytest.fixture
async def event_in_db(db_connection: AsyncSession) -> Event:
    existing_event = EventFactory.build()

    db_connection.add(existing_event)
    await db_connection.commit()
    await db_connection.refresh(existing_event)

    return existing_event


@pytest.fixture
async def ticket_type_in_db(
    db_connection: AsyncSession, event_in_db: Event
) -> TicketType:
    ticket_type = TicketTypeFactory.build(event=event_in_db)

    db_connection.add(ticket_type)
    await db_connection.commit()
    await db_connection.refresh(ticket_type)

    return ticket_type


@pytest.fixture
async def ticket_in_db(
    db_connection: AsyncSession, ticket_type_in_db: TicketType, user_in_db: User
) -> Ticket:
    ticket = TicketFactory.build(ticket_type=ticket_type_in_db, owner=user_in_db)

    db_connection.add(ticket)
    await db_connection.commit()
    await db_connection.refresh(ticket)

    return ticket


@pytest.fixture
async def test_session_factory(
    db_connection: AsyncSession,
) -> async_sessionmaker[AsyncSession]:
    async_bind = db_connection.bind

    engine = async_bind.engine if hasattr(async_bind, "engine") else async_bind

    return async_sessionmaker(bind=engine, expire_on_commit=False)


@pytest.fixture
async def stress_client(
    client: AsyncClient,
    test_session_factory: async_sessionmaker[AsyncSession],
) -> AsyncClient:
    async def override_get_db_concurrent() -> AsyncGenerator[AsyncSession, None]:
        async with test_session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db_concurrent

    return client


@pytest.fixture
def bypass_auth(superuser: User) -> Generator[None, None, None]:
    app.dependency_overrides[get_current_user] = lambda: superuser
    yield
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
async def cleanup_physical_db(
    test_session_factory: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[None, None]:
    yield
    async with test_session_factory() as session:
        await session.execute(delete(Ticket))
        await session.execute(delete(TicketType))
        await session.execute(delete(Event))
        await session.commit()


@pytest.fixture
def api_client(request: pytest.FixtureRequest) -> AsyncClient:
    return cast(AsyncClient, request.getfixturevalue(request.param))
