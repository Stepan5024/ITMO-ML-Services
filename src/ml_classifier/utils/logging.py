"""Logging configuration for the application."""
import os
import sys
from datetime import datetime
from enum import Enum

from loguru import logger


class LogLevel(str, Enum):
    """Log levels."""

    TRACE = "TRACE"
    DEBUG = "DEBUG"
    INFO = "INFO"
    SUCCESS = "SUCCESS"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogConfig:
    """Logging configuration."""

    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_DIR: str = os.getenv("LOG_DIR", "logs")
    LOG_ROTATION: str = os.getenv("LOG_ROTATION", "10 MB")
    LOG_RETENTION: str = os.getenv("LOG_RETENTION", "30 days")
    LOG_FORMAT: str = os.getenv(
        "LOG_FORMAT",
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>",
    )


def setup_logging() -> None:
    """Configure logging for the application."""
    logger.remove()

    os.makedirs(LogConfig.LOG_DIR, exist_ok=True)

    logger.add(
        sys.stderr,
        format=LogConfig.LOG_FORMAT,
        level=LogConfig.LOG_LEVEL,
        colorize=True,
        backtrace=True,
        diagnose=True,
    )

    logger.add(
        os.path.join(LogConfig.LOG_DIR, "ml_classifier_{time}.log"),
        rotation=LogConfig.LOG_ROTATION,
        retention=LogConfig.LOG_RETENTION,
        format=LogConfig.LOG_FORMAT,
        level=LogConfig.LOG_LEVEL,
        compression="zip",
        backtrace=True,
        diagnose=True,
    )

    logger.add(
        os.path.join(LogConfig.LOG_DIR, "ml_classifier_error_{time}.log"),
        rotation=LogConfig.LOG_ROTATION,
        retention=LogConfig.LOG_RETENTION,
        format=LogConfig.LOG_FORMAT,
        level="ERROR",
        filter=lambda record: record["level"].name == "ERROR"
        or record["level"].name == "CRITICAL",
        compression="zip",
        backtrace=True,
        diagnose=True,
    )

    log_app_startup()


def log_app_startup() -> None:
    """Log application startup with environment details."""
    env = os.getenv("ENVIRONMENT", "development")
    logger.info(f"ML Classifier Service starting up in {env} environment")
    logger.debug(f"Log level: {LogConfig.LOG_LEVEL}")
    logger.debug(f"Log directory: {LogConfig.LOG_DIR}")


def get_request_id() -> str:
    """Generate a unique request ID."""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
    return f"req-{timestamp}"
