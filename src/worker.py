import asyncio
import time
from collections import Counter
from datetime import UTC, datetime, timedelta
from typing import Any

from arq import cron
from arq.connections import RedisSettings
from prometheus_client import start_http_server
from redis.asyncio import Redis
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.core import logger, settings
from src.core.metrics import TICKETS_CANCELED_TOTAL, monitor_task
from src.core.metrics.worker import monitor_queue_depth
from src.core.redis_keys import RedisKeys
from src.models import Ticket, TicketType
from src.models.ticket import TicketStatus


async def startup(ctx: dict[str, Any]) -> None:
    """Initialize infrastructure connections for the ARQ worker pool.

    Creates the async SQLAlchemy engine and session maker that will be
    injected into the context of all background tasks.
    """
    logger.info("Starting Arq Worker...")

    start_http_server(8001)
    logger.info(f"Prometheus metrics server started on port {8001}")
    engine = create_async_engine(
        settings.DATABASE_URL, echo=settings.ENVIRONMENT == "dev", future=True
    )

    ctx["engine"] = engine
    ctx["session_maker"] = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
    )

    ctx["queue_monitor_task"] = asyncio.create_task(monitor_queue_depth(ctx["redis"]))

    logger.info("Worker started")


async def shutdown(ctx: dict[str, Any]) -> None:
    """Gracefully close infrastructure connections during worker termination."""
    logger.info("Shutting down Arq Worker...")

    engine = ctx["engine"]
    await engine.dispose()

    logger.info("Worker shut down")


@monitor_task("release_unpaid_ticket")
async def release_unpaid_ticket(ctx: dict[Any, Any], ticket_id: int) -> None:
    """Targeted background task to release a specific unpaid ticket reservation.

    Executed after a predefined timeout. Checks if the ticket is still in
    the 'RESERVED' state. If so, cancels the ticket and increments the
    available inventory for the associated ticket type.

    Args:
        ctx: The ARQ worker context containing the database session maker.
        ticket_id: The ID of the ticket to verify and potentially cancel.

    Raises:
        Exception: If the database transaction or inventory restoration fails.
    """
    session_maker = ctx["session_maker"]
    redis: Redis = ctx["redis"]

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

            ticket_type_id = ticket.ticket_type_id
            ticket.status = TicketStatus.CANCELED

            update_query = (
                update(TicketType)
                .where(TicketType.id == ticket_type_id)
                .values(tickets_sold=TicketType.tickets_sold - 1)
            )
            await session.execute(update_query)

            await RedisKeys.refund_inventory_idempotent(
                redis=redis, ticket_type_id=ticket_type_id, ticket_id=ticket.id
            )

            await session.commit()

            TICKETS_CANCELED_TOTAL.labels(reason="timeout").inc()
            logger.info(
                f"Worker Task: Ticket {ticket_id} successfully CANCELED due to timeout"
            )
        except Exception as e:
            await session.rollback()
            logger.error(
                f"Worker Task: Failed to release ticket {ticket_id}. Error: {e}"
            )
            raise


@monitor_task("reconcile_hung_tickets")
async def reconcile_hung_tickets(ctx: dict[Any, Any]) -> None:
    """Periodic garbage collection task for stuck reservations.

    Runs as a cron job to find any tickets that remained in 'RESERVED' status
    past the expiration threshold (e.g., if the specific `release_unpaid_ticket`
    task failed or was dropped). Cancels the stuck tickets and performs a
    batch update to restore the inventory correctly.

    Args:
        ctx: The ARQ worker context containing the database session maker.
    """
    session_maker = ctx["session_maker"]
    redis: Redis = ctx["redis"]

    threshold = datetime.now(UTC) - timedelta(
        seconds=settings.TICKET_RESERVATION_TIME_SECONDS
    )

    async with session_maker() as session:
        cancel_query = (
            update(Ticket)
            .where(Ticket.status == TicketStatus.RESERVED)
            .where(Ticket.created_at <= threshold)
            .values(status=TicketStatus.CANCELED)
            .returning(Ticket.id, Ticket.ticket_type_id)
        )
        result = await session.execute(cancel_query)
        canceled_tickets = result.all()

        if not canceled_tickets:
            return

        logger.info(f"Garbage collector: Found {len(canceled_tickets)} hung tickets")

        type_count = Counter(t.ticket_type_id for t in canceled_tickets)

        for ticket_type_id, count in type_count.items():
            refund_query = (
                update(TicketType)
                .where(TicketType.id == ticket_type_id)
                .values(tickets_sold=TicketType.tickets_sold - count)
            )
            await session.execute(refund_query)

        for ticket_id, ticket_type_id in canceled_tickets:
            await RedisKeys.refund_inventory_idempotent(
                redis=redis, ticket_type_id=ticket_type_id, ticket_id=ticket_id
            )

        await session.commit()

        TICKETS_CANCELED_TOTAL.labels("garbage_collector").inc(len(canceled_tickets))
        logger.info("Garbage Collector: Successfully returned tickets to DB and Redis")


@monitor_task("reconcile_redis_orphans")
async def reconcile_redis_orphans(ctx: dict[Any, Any]) -> None:
    """Find and refund orphaned reservations in Redis.

    Uses a grace period to prevent race conditions with slow database transactions.
    """
    session_maker = ctx["session_maker"]
    redis: Redis = ctx["redis"]

    active_redis_locks = await RedisKeys.get_all_active_reservations(redis)

    if not active_redis_locks:
        return

    current_time = int(time.time())
    GRACE_PERIOD_SECONDS = 60

    suspicious_locks = [
        lock
        for lock in active_redis_locks
        if (current_time - lock["timestamp"]) > GRACE_PERIOD_SECONDS
    ]

    if not suspicious_locks:
        return

    redis_ticket_ids = [lock["ticket_id"] for lock in suspicious_locks]

    async with session_maker() as session:
        query = select(Ticket.id, Ticket.status).where(Ticket.id.in_(redis_ticket_ids))
        result = await session.execute(query)
        db_tickets = {row.id: row.status for row in result.all()}

    orphaned_locks = []

    for lock in suspicious_locks:
        ticket_id = lock["ticket_id"]
        db_status = db_tickets.get(ticket_id)

        if db_status is None or db_status == TicketStatus.CANCELED:
            orphaned_locks.append(lock)

    logger.info(f"Redis GC: Found {len(orphaned_locks)} ghost locks")

    if not orphaned_locks:
        return

    for lock in orphaned_locks:
        await RedisKeys.refund_inventory_idempotent(
            redis=redis,
            ticket_type_id=lock["ticket_type_id"],
            ticket_id=lock["ticket_id"],
        )

    logger.info("Redis GC: Ghost tickets refunded successfully")


class WorkerSettings:
    """Configuration class for the ARQ Redis worker."""

    redis_settings = RedisSettings(
        host=settings.REDIS_HOST, port=settings.REDIS_PORT, database=1
    )

    functions = [release_unpaid_ticket]
    on_startup = startup
    on_shutdown = shutdown

    cron_jobs = [
        cron(reconcile_hung_tickets, minute=set(range(0, 60, 5))),
        cron(reconcile_redis_orphans, minute=set(range(2, 60, 5))),
    ]
