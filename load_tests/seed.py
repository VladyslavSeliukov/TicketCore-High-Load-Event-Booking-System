import asyncio
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.core.config import settings
from src.core.security import get_password_hash
from src.models.event import Event
from src.models.ticket_type import TicketType
from src.models.user import User

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

USERS_COUNT = 10_000
TEST_PASSWORD = "extreamly_strong_password"
BATCH_SIZE = 5_000


async def seed_db(engine: AsyncEngine) -> None:
    """Populate the database with initial load-testing data."""
    AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
        bind=engine,
        expire_on_commit=False,
        autoflush=False,
    )

    logger.info("Generating valid password hash...")
    real_password_hash = get_password_hash(TEST_PASSWORD)

    async with AsyncSessionLocal() as session:
        async with session.begin():
            stmt = select(Event).where(Event.title == "Rammstein: Europe Stadium Tour")
            existing_event = (await session.execute(stmt)).scalar_one_or_none()

            if not existing_event:
                logger.info("Creating Event...")
                event = Event(
                    title="Rammstein: Europe Stadium Tour",
                    date=datetime.now(UTC) + timedelta(days=30),
                    country="Poland",
                    city="Wrocław",
                    street_address="Tarczyński Arena",
                )
                session.add(event)
                await session.flush()
            else:
                logger.info("Event already exists.")
                event = existing_event

            tt_stmt = select(TicketType).where(TicketType.event_id == event.id)
            existing_tts = (await session.execute(tt_stmt)).scalars().all()

            if not existing_tts:
                logger.info("Creating Ticket Types...")
                ticket_types = [
                    TicketType(
                        event_id=event.id,
                        name="Fan Zone",
                        price=15000,
                        tickets_quantity=5000,
                        tickets_sold=0,
                    ),
                    TicketType(
                        event_id=event.id,
                        name="VIP",
                        price=50000,
                        tickets_quantity=500,
                        tickets_sold=0,
                    ),
                ]
                session.add_all(ticket_types)
                await session.flush()
                tt_ids = [tt.id for tt in ticket_types]
            else:
                logger.info("Ticket Types already exist.")
                tt_ids = [tt.id for tt in existing_tts]

            user_check = await session.execute(select(User.id).limit(1))
            if not user_check.scalar_one_or_none():
                logger.info(f"Preparing to insert {USERS_COUNT} users...")
                users_data: list[dict[str, Any]] = [
                    {
                        "email": f"loadtest_{i}@example.com",
                        "hashed_password": real_password_hash,
                        "is_active": True,
                    }
                    for i in range(1, USERS_COUNT + 1)
                ]

                for i in range(0, len(users_data), BATCH_SIZE):
                    batch = users_data[i : i + BATCH_SIZE]
                    await session.execute(insert(User).values(batch))
            else:
                logger.info("Users already seeded.")

            logger.info("Database seeded successfully!")
            logger.info(f"--- TARGET_EVENT_ID = {event.id}")
            logger.info(f"--- AVAILABLE_TICKET_TYPES = {tt_ids}")


async def main() -> None:
    """Entry point for the database seeding script."""
    engine = create_async_engine(str(settings.DATABASE_URL), pool_pre_ping=True)
    try:
        await seed_db(engine)
    except Exception as e:
        logger.error(f"Seeding failed: {e}")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
