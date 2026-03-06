from typing import Any

from arq.connections import RedisSettings
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.core import logger, settings
from src.models import Ticket, TicketType
from src.models.ticket import TicketStatus


async def startup(ctx: dict[str, Any]) -> None:
    logger.info("Starting Arq Worker...")

    engine = create_async_engine(
        settings.DATABASE_URL, echo=settings.ENVIRONMENT == "dev", future=True
    )

    ctx["engine"] = engine
    ctx["session_maker"] = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
    )


async def shutdown(ctx: dict[str, Any]) -> None:
    logger.info("Shutting down Arq Worker...")

    engine = ctx["engine"]
    await engine.dispose()


async def release_unpaid_ticket(ctx: dict[str, Any], ticket_id: int) -> None:
    session_maker = ctx["session_maker"]

    async with session_maker() as session:
        try:
            query = select(Ticket).where(Ticket.id == ticket_id).with_for_update()
            ticket = await session.scalar(query)

            if not ticket:
                logger.info(f"Worker Task: Ticket {ticket_id} not found")
                return

            if ticket.status != TicketStatus.RESERVED:
                logger.info(
                    f"Worker Task: Ticket {ticket_id} has status {ticket.status.name}. "
                    f"Skipping"
                )
                return

            ticket.status = TicketStatus.CANCELED

            update_query = (
                update(TicketType)
                .where(TicketType.id == ticket.ticket_type_id)
                .values(tickets_sold=TicketType.tickets_sold - 1)
            )
            await session.execute(update_query)
            await session.commit()

            logger.info(
                f"Worker Task: Ticket {ticket_id} successfully CANCELED due to timeout"
            )
        except Exception as e:
            await session.rollback()
            logger.error(
                f"Worker Task: Failed to release ticket {ticket_id}. Error: {e}"
            )
            raise


class WorkerSettings:
    redis_settings = RedisSettings(
        host=settings.REDIS_HOST, port=settings.REDIS_PORT, database=1
    )

    functions = [release_unpaid_ticket]
    on_startup = startup
    on_shutdown = shutdown
