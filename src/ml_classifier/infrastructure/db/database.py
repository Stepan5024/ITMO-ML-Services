# src/ml_classifier/infrastructure/db/database.py
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import text

# Create the SQLAlchemy base model
Base = declarative_base()

# Формирование URL для подключения к базе данных - MODIFIED THIS LINE
# Database connection details from environment
DATABASE_USER = os.getenv("POSTGRES_USER", "ml_user")
DATABASE_PASSWORD = os.getenv("POSTGRES_PASSWORD", "change_this_password")
DATABASE_HOST = os.getenv("POSTGRES_HOST", "postgres")
DATABASE_PORT = os.getenv("POSTGRES_PORT", "5432")
DATABASE_NAME = os.getenv("POSTGRES_DB", "ml_classifier_db")

# Use ASYNC_DATABASE_URL for the async engine
ASYNC_DATABASE_URL = os.getenv(
    "ASYNC_DATABASE_URL",
    f"postgresql+asyncpg://{DATABASE_USER}:{DATABASE_PASSWORD}@{DATABASE_HOST}:{DATABASE_PORT}/{DATABASE_NAME}",
)

# Create the async engine
engine = create_async_engine(
    ASYNC_DATABASE_URL,
    echo=os.getenv("SQL_ECHO", "False").lower() == "true",
    pool_pre_ping=True,
    pool_size=int(os.getenv("DATABASE_POOL_SIZE", "5")),
    max_overflow=int(os.getenv("DATABASE_MAX_OVERFLOW", "10")),
)

# Создание фабрики сессий
AsyncSessionMaker = async_sessionmaker(
    engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Асинхронный контекстный менеджер для получения сессии базы данных.

    Yields:
        AsyncSession: Асинхронная сессия базы данных.
    """
    session = AsyncSessionMaker()
    try:
        logger.debug("Database session created")
        yield session
    finally:
        await session.close()
        logger.debug("Database session closed")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Асинхронный генератор для использования в Depends FastAPI.

    Yields:
        AsyncSession: Асинхронная сессия базы данных.
    """
    async with get_db_session() as session:
        yield session


async def check_database_connection() -> bool:
    """
    Проверка соединения с базой данных.

    Returns:
        bool: True, если соединение успешно, иначе False.
    """
    try:
        async with get_db_session() as session:
            await session.execute(text("SELECT 1"))
            logger.info("Database connection successful")
            return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False


async def init_db() -> None:
    """
    Инициализация базы данных при запуске приложения.
    Может использоваться для выполнения начальных проверок или миграций.
    """
    if await check_database_connection():
        logger.info("Database initialized successfully")
    else:
        logger.error("Failed to initialize database")
