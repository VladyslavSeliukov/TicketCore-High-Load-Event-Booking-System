from collections.abc import Iterator
from typing import cast

from prometheus_client.core import GaugeMetricFamily
from sqlalchemy import QueuePool
from sqlalchemy.ext.asyncio import AsyncEngine


class SQLAlchemyPoolCollector:
    """Collector for gathering SQLAlchemy database connection pool metrics.

    Extracts internal state from the connection pool (like total size,
    checked in/out connections) and exposes them to Prometheus.
    """

    def __init__(self, engine: AsyncEngine) -> None:
        self.pool = cast(QueuePool, engine.pool)

    def collect(self) -> Iterator[GaugeMetricFamily]:
        """Collect current database pool metrics.

        Yields:
            GaugeMetricFamily: The generated Prometheus metrics for the pool.
        """
        yield GaugeMetricFamily(
            "db_pool_size",
            "Maximum number of persistent connections in the pool",
            value=self.pool.size(),
        )
        yield GaugeMetricFamily(
            "db_pool_checkedin",
            "Number of connections currently idle and available",
            value=self.pool.checkedin(),
        )
        yield GaugeMetricFamily(
            "db_pool_checkedout",
            "Number of connections currently in use by the application",
            value=self.pool.checkedout(),
        )
        yield GaugeMetricFamily(
            "db_pool_overflow",
            "Number of connections created beyond the base pool_size",
            value=self.pool.overflow(),
        )
