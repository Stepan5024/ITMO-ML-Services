"""Common fixtures for testing."""
import asyncio
import uuid
from decimal import Decimal
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from ml_classifier.domain.entities.user import User
from ml_classifier.infrastructure.security.jwt import create_access_token
from ml_classifier.main import app as fastapi_app

# Use in-memory SQLite for tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an event loop for tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_db_engine():
    """Create a test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        future=True,
        echo=False,
    )
    yield engine
    await engine.dispose()


@pytest.fixture
async def test_db_session(test_db_engine):
    """Create a test database session."""
    from ml_classifier.infrastructure.db.database import Base

    # Create all tables
    async with test_db_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create a session
    async_session_maker = sessionmaker(
        test_db_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session_maker() as session:
        yield session

    # Drop all tables
    async with test_db_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
def app():
    """Return the FastAPI application."""
    return fastapi_app


@pytest.fixture
def client(app):
    """Return a test client for the FastAPI application."""
    return TestClient(app)


@pytest.fixture
def test_user() -> User:
    """Create a test user entity."""
    return User(
        id=uuid.uuid4(),
        email="test@example.com",
        hashed_password="$2b$12$EcwZLNh9S4Kqu/r0U1vZ9Oef5ZUu830AZ7O2CJ33V06JdNjnz9/2S",  # hashed 'Password123'
        full_name="Test User",
        is_active=True,
        is_admin=False,
        balance=Decimal("100.00"),
    )


@pytest.fixture
def test_admin() -> User:
    """Create a test admin entity."""
    return User(
        id=uuid.uuid4(),
        email="admin@example.com",
        hashed_password="$2b$12$EcwZLNh9S4Kqu/r0U1vZ9Oef5ZUu830AZ7O2CJ33V06JdNjnz9/2S",  # hashed 'Password123'
        full_name="Admin User",
        is_active=True,
        is_admin=True,
        balance=Decimal("500.00"),
    )


@pytest.fixture
def valid_token(test_user) -> str:
    """Create a valid JWT token for the test user."""
    return create_access_token(
        subject=test_user.id,
        email=test_user.email,
    )


@pytest.fixture
def admin_token(test_admin) -> str:
    """Create a valid JWT token for the admin user."""
    return create_access_token(
        subject=test_admin.id,
        email=test_admin.email,
        is_admin=test_admin.is_admin,
    )
