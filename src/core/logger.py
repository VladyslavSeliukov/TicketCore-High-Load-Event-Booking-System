import json
import logging
import sys
from datetime import UTC, datetime

from src.core.config import settings


class JsonFormatter(logging.Formatter):
    """Formatter that serializes log records into structured JSON objects.

    Captures metadata (timestamp, module, line) and exception traces,
    making the logs suitable for ingestion by centralized logging systems
    (e.g., ELK stack, Datadog).
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record as a JSON string."""
        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "module": record.module,
            "line": record.lineno,
        }

        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        if hasattr(record, "extra_data"):
            log_entry.update(record.extra_data)

        return json.dumps(log_entry)


class ConsoleFormatter(logging.Formatter):
    """Formatter that applies ANSI color codes to standard console output.

    Improves readability during local development by coloring log levels
    (e.g., red for errors, yellow for warnings).
    """

    grey = "\x1b[38;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    format_str = "%(levelname)s:     [%(module)s:%(lineno)d] %(message)s"

    FORMATS = {
        logging.DEBUG: grey + format_str + reset,
        logging.INFO: grey + format_str + reset,
        logging.WARNING: yellow + format_str + reset,
        logging.ERROR: red + format_str + reset,
        logging.CRITICAL: bold_red + format_str + reset,
    }

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record with ANSI color codes."""
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)

        return formatter.format(record)


def get_logger(name: str) -> logging.Logger:
    """Retrieve or create a globally configured logger instance.

    Prevents the duplication of handlers on multiple calls and dynamically
    sets the log level based on the application's environment settings.

    Args:
        name: The name of the logger (typically `__name__` of the calling module).

    Returns:
        A configured standard Python Logger instance.
    """
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    try:
        log_level = settings.LOG_LEVEL.upper()
        logger.setLevel(getattr(logging, log_level))
    except AttributeError:
        logger.setLevel(logging.INFO)

    handler = logging.StreamHandler(sys.stdout)

    if settings.ENVIRONMENT == "prod":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(ConsoleFormatter())

    logger.addHandler(handler)

    logger.propagate = False

    return logger


logger = get_logger("ticketcore")
