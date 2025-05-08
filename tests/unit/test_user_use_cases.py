"""Unit tests for user use cases."""
import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from passlib.context import CryptContext

from ml_classifier.domain.entities.user import User
from ml_classifier.domain.repositories.user_repository import UserRepository
from ml_classifier.services.user_use_cases import UserUseCase


@pytest.fixture
def mock_user_repository():
    """Fixture to create a mock user repository."""
    repo = AsyncMock(spec=UserRepository)
    return repo


@pytest.fixture
def user_use_case(mock_user_repository):
    """Fixture to create a UserUseCase instance."""
    return UserUseCase(mock_user_repository)


@pytest.fixture
def sample_user():
    """Fixture to create a sample user for testing."""
    user_id = uuid.uuid4()
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    hashed_password = pwd_context.hash("StrongPass123")
    return User(
        id=user_id,
        email="test@example.com",
        hashed_password=hashed_password,
        full_name="Test User",
        is_active=True,
        is_admin=False,
        balance=Decimal("100.00"),
    )


class TestUserUseCase:
    """Tests for UserUseCase functionality."""

    @pytest.mark.asyncio
    async def test_register_user_success(self, user_use_case, mock_user_repository):
        """Test successful user registration."""
        # Setup
        mock_user_repository.get_by_email.return_value = None
        mock_user_repository.create.return_value = User(
            id=uuid.uuid4(),
            email="new@example.com",
            hashed_password="hashed_password",
            full_name="New User",
            is_active=True,
        )

        # Execute
        success, message, user = await user_use_case.register_user(
            "new@example.com", "StrongPass123", "New User"
        )

        # Assert
        assert success is True
        assert "successfully" in message.lower()
        assert user is not None
        assert user.email == "new@example.com"
        assert user.full_name == "New User"
        mock_user_repository.get_by_email.assert_called_once_with("new@example.com")
        mock_user_repository.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_register_user_duplicate_email(
        self, user_use_case, mock_user_repository, sample_user
    ):
        """Test user registration with existing email."""
        # Setup
        mock_user_repository.get_by_email.return_value = sample_user

        # Execute
        success, message, user = await user_use_case.register_user(
            "test@example.com", "StrongPass123", "New User"
        )

        # Assert
        assert success is False
        assert "already registered" in message.lower()
        assert user is None
        mock_user_repository.get_by_email.assert_called_once_with("test@example.com")
        mock_user_repository.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_register_user_weak_password(
        self, user_use_case, mock_user_repository
    ):
        """Test user registration with weak password."""
        # Execute
        success, message, user = await user_use_case.register_user(
            "new@example.com", "weak", "New User"
        )

        # Assert
        assert success is False
        assert "password" in message.lower()
        assert user is None
        mock_user_repository.get_by_email.assert_not_called()
        mock_user_repository.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_authenticate_user_success(
        self, user_use_case, mock_user_repository, sample_user
    ):
        """Test successful user authentication."""
        # Setup
        mock_user_repository.get_by_email.return_value = sample_user

        # Mock verify_password on the User entity
        with patch.object(User, "verify_password", return_value=True):
            # Execute
            user = await user_use_case.authenticate_user(
                "test@example.com", "StrongPass123"
            )

            # Assert
            assert user is not None
            assert user.email == "test@example.com"
            mock_user_repository.get_by_email.assert_called_once_with(
                "test@example.com"
            )

    @pytest.mark.asyncio
    async def test_authenticate_user_wrong_password(
        self, user_use_case, mock_user_repository, sample_user
    ):
        """Test authentication with wrong password."""
        # Setup
        mock_user_repository.get_by_email.return_value = sample_user

        # Mock verify_password on the User entity
        with patch.object(User, "verify_password", return_value=False):
            # Execute
            user = await user_use_case.authenticate_user(
                "test@example.com", "WrongPass123"
            )

            # Assert
            assert user is None
            mock_user_repository.get_by_email.assert_called_once_with(
                "test@example.com"
            )

    @pytest.mark.asyncio
    async def test_authenticate_user_not_found(
        self, user_use_case, mock_user_repository
    ):
        """Test authentication with non-existent user."""
        # Setup
        mock_user_repository.get_by_email.return_value = None

        # Execute
        user = await user_use_case.authenticate_user(
            "nonexistent@example.com", "StrongPass123"
        )

        # Assert
        assert user is None
        mock_user_repository.get_by_email.assert_called_once_with(
            "nonexistent@example.com"
        )

    @pytest.mark.asyncio
    async def test_get_user_by_id(
        self, user_use_case, mock_user_repository, sample_user
    ):
        """Test getting user by ID."""
        # Setup
        mock_user_repository.get_by_id.return_value = sample_user

        # Execute
        user = await user_use_case.get_user_by_id(sample_user.id)

        # Assert
        assert user is not None
        assert user.id == sample_user.id
        mock_user_repository.get_by_id.assert_called_once_with(sample_user.id)

    @pytest.mark.asyncio
    async def test_change_password_success(
        self, user_use_case, mock_user_repository, sample_user
    ):
        """Test successful password change."""
        # Setup
        mock_user_repository.get_by_id.return_value = sample_user
        mock_user_repository.update.return_value = sample_user

        # Mock verify_password on the User entity
        with patch.object(User, "verify_password", return_value=True):
            # Execute
            success, message = await user_use_case.change_password(
                sample_user.id, "CurrentPass123", "NewStrongPass123"
            )

            # Assert
            assert success is True
            assert "successfully" in message.lower()
            mock_user_repository.get_by_id.assert_called_once_with(sample_user.id)
            mock_user_repository.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_change_password_wrong_current(
        self, user_use_case, mock_user_repository, sample_user
    ):
        """Test password change with wrong current password."""
        # Setup
        mock_user_repository.get_by_id.return_value = sample_user

        # Mock verify_password on the User entity
        with patch.object(User, "verify_password", return_value=False):
            # Execute
            success, message = await user_use_case.change_password(
                sample_user.id, "WrongCurrentPass", "NewStrongPass123"
            )

            # Assert
            assert success is False
            assert "incorrect" in message.lower()
            mock_user_repository.get_by_id.assert_called_once_with(sample_user.id)
            mock_user_repository.update.assert_not_called()

    @pytest.mark.asyncio
    async def test_change_password_weak_new(
        self, user_use_case, mock_user_repository, sample_user
    ):
        """Test password change with weak new password."""
        # Setup
        mock_user_repository.get_by_id.return_value = sample_user

        # Mock verify_password on the User entity
        with patch.object(User, "verify_password", return_value=True):
            # Execute
            success, message = await user_use_case.change_password(
                sample_user.id, "CurrentPass123", "weak"
            )

            # Assert
            assert success is False
            assert "password" in message.lower()
            mock_user_repository.get_by_id.assert_called_once_with(sample_user.id)
            mock_user_repository.update.assert_not_called()
