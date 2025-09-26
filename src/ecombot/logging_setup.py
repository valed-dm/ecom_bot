"""
Configures the Loguru logger to be the primary logging backend for the application.

This module provides a single setup function that replaces Django's default
logging with the more powerful and developer-friendly Loguru library.
"""

import sys
from typing import NoReturn

from loguru import logger
from loguru._logger import Logger

from .config import OUTPUT_DIR
from .config import settings


def _setup_logging() -> Logger:
    """
    Initializes and configures the Loguru logger for the entire application.

    This function should be called once at the application's entry point
    (e.g., in `settings.py`). It sets up two primary "sinks": one for writing
    detailed, structured logs to a file, and another for writing colorful,
    human-readable logs to the console.

    Returns:
        The configured Loguru logger instance.
    """
    logger.remove()

    try:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        _critical_exit(f"Failed to create log directory {OUTPUT_DIR}: {e}")

    logger.add(
        sink=settings.LOG_FILE,
        level=settings.LOG_LEVEL.upper(),
        format=(
            "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level:<8} | "
            "{name}:{function}:{line} - {message}"
        ),
        rotation="1 MB",
        enqueue=True,
        backtrace=settings.DEBUG,
        diagnose=settings.DEBUG,
        catch=True,
    )

    logger.add(
        sink=sys.stderr,
        level="INFO",
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level:<8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>"
        ),
        colorize=True,
    )

    return logger  # type: ignore


def _critical_exit(message: str) -> NoReturn:
    """
    A helper function to print a critical error to stderr and exit the program.

    Used for unrecoverable startup errors.
    """
    sys.stderr.write(f"FATAL: {message}\n")
    sys.exit(1)


log = _setup_logging()
