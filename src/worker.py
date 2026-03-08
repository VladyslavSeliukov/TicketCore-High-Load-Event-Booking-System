from collections import Counter
from datetime import UTC, datetime, timedelta
from typing import Any

from arq import cron
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
    logger.info("Worker started")


async def shutdown(ctx: dict[str, Any]) -> None:
    logger.info("Shutting down Arq Worker...")

    engine = ctx["engine"]
    await engine.dispose()

    logger.info("Worker shut down")


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


async def reconcile_hung_tickets(ctx: dict[str, Any]) -> None:
    session_maker = ctx["session_maker"]
    threshold = datetime.now(UTC) - timedelta(
        seconds=settings.TICKET_RESERVATION_TIME_SECONDS
    )

    async with session_maker() as session:
        cancel_query = (
            update(Ticket)
            .where(Ticket.status == TicketStatus.RESERVED)
            .where(Ticket.created_at <= threshold)
            .values(status=TicketStatus.CANCELED)
            .returning(Ticket.ticket_type_id)
        )
        result = await session.execute(cancel_query)
        canceled_ticket_types = result.scalars().all()

        if not canceled_ticket_types:
            return

        logger.info(
            f"Garbage collector: Found {len(canceled_ticket_types)} hung tickets"
        )
        type_count = Counter(canceled_ticket_types)

        for ticket_type_id, count in type_count.items():
            refund_query = (
                update(TicketType)
                .where(TicketType.id == ticket_type_id)
                .values(tickets_sold=TicketType.tickets_sold - count)
            )
            await session.execute(refund_query)
        await session.commit()
        logger.info("Garbage Collector: Successfully returned tickets")


class WorkerSettings:
    redis_settings = RedisSettings(
        host=settings.REDIS_HOST, port=settings.REDIS_PORT, database=1
    )

    functions = [release_unpaid_ticket]
    on_startup = startup
    on_shutdown = shutdown

    cron_jobs = [cron(reconcile_hung_tickets, minute=set(range(0, 60, 5)))]
