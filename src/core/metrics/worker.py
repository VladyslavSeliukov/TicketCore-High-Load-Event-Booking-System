import asyncio
import time
from collections.abc import Awaitable, Callable, Coroutine
from typing import Any, ParamSpec, TypeVar, cast

from arq.constants import default_queue_name
from prometheus_client import Counter, Gauge, Histogram
from redis.asyncio import Redis

from src.core import logger

P = ParamSpec("P")
T = TypeVar("T")

WORKER_TASKS_TOTAL = Counter(
    "worker_tasks_total",
    "Total number of background tasks executed",
    ["task_name", "status"],
)
WORKER_TASK_DURATION = Histogram(
    "worker_task_duration_second",
    "Duration of background tasks",
    ["task_name"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0),
)

ARQ_QUEUE_DEPTH = Gauge("arq_queue_depth", "Number of pending tasks in the ARQ queue")


def monitor_task(
    task_name: str,
) -> Callable[
    [Callable[P, Coroutine[Any, Any, T]]], Callable[P, Coroutine[Any, Any, T]]
]:
    """Decorator for collecting Prometheus metrics on ARQ worker tasks.

    Wraps an asynchronous background task to automatically measure its execution time
    and track its completion status (success or error). Exposes these metrics
    via Prometheus counters and histograms.

    Args:
        task_name: A unique string identifier for the task, used as label in Prometheus.

    Returns:
        Callable[[Callable[P, Awaitable[T]]], Callable[P, Awaitable[T]]]:
        The decorated asynchronous function.
    """

    def decorator(
        func: Callable[P, Coroutine[Any, Any, T]],
    ) -> Callable[P, Coroutine[Any, Any, T]]:
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            start_time: float = time.time()
            status: str = "success"
            try:
                return await func(*args, **kwargs)
            except Exception:
                status = "error"
                raise
            finally:
                duration: float = time.time() - start_time
                WORKER_TASK_DURATION.labels(task_name=task_name).observe(duration)
                WORKER_TASKS_TOTAL.labels(task_name=task_name, status=status).inc()

        return wrapper

    return decorator


async def monitor_queue_depth(redis: Redis) -> None:
    """Background task for continuously monitoring the ARQ Redis queue depth.

    Runs as an infinite loop polling the Redis list representing the default ARQ queue.
    Updates the `arq_queue_depth` Prometheus Gauge every 5 seconds. Designed to be
    run concurrently with the main worker process.

    Args:
        redis: An active asynchronous Redis client instance.
    """
    while True:
        try:
            queue_length: int = await cast(
                Awaitable[int], redis.llen(default_queue_name)
            )
            ARQ_QUEUE_DEPTH.set(queue_length)
            await asyncio.sleep(5)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Metrics: Failed to collect ARQ queue depth. Error: {e}")
            await asyncio.sleep(5)
