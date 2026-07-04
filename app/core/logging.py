"""
Centralized logging configuration.

Call `setup_logging()` once at application startup (in main.py and in the
Celery worker entrypoint). After that, use standard Python logging anywhere:

    import logging
    logger = logging.getLogger(__name__)
    logger.info("Processing job", extra={"job_id": job_id})

All output will be structured JSON, ready for log aggregation systems.
"""

import logging
import sys

from pythonjsonlogger import jsonlogger

from app.config import settings


def setup_logging() -> None:
    """
    Configures the root Python logger to emit structured JSON.

    This function must be called once before any logging statements run.
    Calling it multiple times is safe — duplicate handlers are avoided.
    """

    # Get the root logger.
    # Python's logging is hierarchical: all loggers (logging.getLogger("app.workers"),
    # logging.getLogger("celery"), etc.) inherit from the root logger.
    # Configuring the root logger affects all loggers in the entire process.
    root_logger = logging.getLogger()

    # Prevent adding duplicate handlers if setup_logging() is called more than once.
    # Each call to setup_logging() would add another handler, causing every log
    # message to be printed multiple times.
    if root_logger.handlers:
        return

    # Set the minimum severity level. Messages below this level are discarded.
    # LOG_LEVEL from .env controls this: DEBUG, INFO, WARNING, ERROR, CRITICAL.
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    root_logger.setLevel(log_level)

    # Create a handler that writes to stdout (standard output).
    # In Docker, stdout is captured by the container runtime and available via
    # `docker compose logs`. Writing to stderr (standard error) would mix log
    # output with Python tracebacks, making both harder to read.
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)

    # The formatter converts a LogRecord object into the final string output.
    # JsonFormatter from python-json-logger replaces the default plain-text
    # formatter with one that outputs JSON.
    #
    # The format string defines which fields appear in every JSON log line.
    # These names match standard log aggregation conventions:
    #   %(asctime)s   → "timestamp": "2024-01-15 10:30:00"
    #   %(name)s      → "logger": "app.workers.tasks"
    #   %(levelname)s → "level": "INFO"
    #   %(message)s   → "message": "Job started"
    formatter = jsonlogger.JsonFormatter(
        fmt="%(asctime)s %(name)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%SZ",  # ISO 8601 format — universal standard
        rename_fields={
            "asctime": "timestamp",
            "name": "logger",
            "levelname": "level",
        },
    )

    handler.setFormatter(formatter)
    root_logger.addHandler(handler)

    # Reduce noise from third-party libraries that log excessively at DEBUG level.
    # These libraries use Python's standard logging, so they inherit our root config.
    # Without these lines, DEBUG mode would flood your terminal with SQLAlchemy's
    # SQL queries and httpx's HTTP request/response details.
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Convenience function to get a named logger.

    Usage in any module:
        from app.core.logging import get_logger
        logger = get_logger(__name__)
        logger.info("Something happened", extra={"job_id": "abc-123"})

    Using __name__ as the logger name automatically sets the logger name to
    the module's dotted path (e.g., "app.workers.tasks"), making it easy to
    trace which module emitted each log line.
    """
    return logging.getLogger(name)