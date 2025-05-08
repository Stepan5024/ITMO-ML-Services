"""Unit tests for user repository implementation."""
import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from ml_classifier.domain.entities.user import User
from ml_classifier.infrastructure.db.repositories.user_repository import (
    SQLAlchemyUserRepository,
)


@pytest.fixture
def mock_db_session():
    """Fixture to create a mock database session."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    return session


@pytest.fixture
def user_repository(mock_db_session):
    """Fixture to create a UserRepository instance with mock session."""
    return SQLAlchemyUserRepository(mock_db_session)


@pytest.fixture
def sample_user():
    """Fixture to create a sample user for testing."""
    return User(
        id=uuid.uuid4(),
        email="test@example.com",
        hashed_password="hashed_password",
        full_name="Test User",
        is_active=True,
        is_admin=False,
        balance=Decimal("100.00"),
    )


class TestUserRepository:
    """Tests for UserRepository implementation."""

    @pytest.mark.asyncio
    async def test_get_by_id_found(self, user_repository, mock_db_session, sample_user):
        """Test getting a user by ID when the user exists."""
        # Setup mock query result
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = MagicMock(
            id=sample_user.id,
            email=sample_user.email,
            hashed_password=sample_user.hashed_password,
            full_name=sample_user.full_name,
            is_active=sample_user.is_active,
            is_admin=sample_user.is_admin,
            balance=float(sample_user.balance),
            created_at=sample_user.created_at,
            updated_at=sample_user.updated_at,
        )
        mock_db_session.execute.return_value = mock_result

        # Execute
        user = await user_repository.get_by_id(sample_user.id)

        # Assert
        assert user is not None
        assert user.id == sample_user.id
        assert user.email == sample_user.email
        mock_db_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, user_repository, mock_db_session):
        """Test getting a user by ID when the user doesn't exist."""
        # Setup mock query result
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None
        mock_db_session.execute.return_value = mock_result

        # Execute
        user = await user_repository.get_by_id(uuid.uuid4())

        # Assert
        assert user is None
        mock_db_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_email_found(
        self, user_repository, mock_db_session, sample_user
    ):
        """Test getting a user by email when the user exists."""
        # Setup mock query result
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = MagicMock(
            id=sample_user.id,
            email=sample_user.email,
            hashed_password=sample_user.hashed_password,
            full_name=sample_user.full_name,
            is_active=sample_user.is_active,
            is_admin=sample_user.is_admin,
            balance=float(sample_user.balance),
            created_at=sample_user.created_at,
            updated_at=sample_user.updated_at,
        )
        mock_db_session.execute.return_value = mock_result

        # Execute
        user = await user_repository.get_by_email(sample_user.email)

        # Assert
        assert user is not None
        assert user.email == sample_user.email
        mock_db_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_user(self, user_repository, mock_db_session, sample_user):
        """Test creating a new user."""
        # Setup mock to capture the added object
        created_db_model = None

        # Create a side effect to capture the object passed to add()
        def capture_added_model(model):
            nonlocal created_db_model
            created_db_model = model

        mock_db_session.add.side_effect = capture_added_model

        # Mock refresh to return the model
        async def mock_refresh(model):
            return model

        mock_db_session.refresh = AsyncMock(side_effect=mock_refresh)

        # Execute
        created_user = await user_repository.create(sample_user)

        # Assert
        assert created_user is not None
        assert created_user.id == sample_user.id
        assert created_user.email == sample_user.email
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()
        assert mock_db_session.refresh.call_count == 1
