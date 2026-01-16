import logging
import sys
import json
from datetime import datetime, timezone
from src.core.config import settings

class JsonFormatter(logging.Formatter):
    def format(self, record:logging.LogRecord) -> str:
        log_entry = {
            'timestamp' : datetime.now(timezone.utc).isoformat(),
            'level' : record.levelname,
            'message' : record.getMessage(),
            'logger' : record.name,
            'module' : record.module,
            'line' : record.lineno
        }

        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)

        if hasattr(record, 'extra_data'):
            log_entry.update(record.extra_data)

        return json.dumps(log_entry)

class ConsoleFormatter(logging.Formatter):
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

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)

        return formatter.format(record)

def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    try:
        log_level = settings.LOG_LEVEL.upper()
        logger.setLevel(getattr(logging, log_level))
    except AttributeError:
        logger.setLevel(logging.INFO)

    handler = logging.StreamHandler(sys.stdout)

    if settings.ENVIRONMENT == 'prod':
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(ConsoleFormatter())

    logger.addHandler(handler)

    logger.propagate = False

logger = get_logger('ticketcore')