"""Unit tests for admin user use cases."""
import uuid
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from ml_classifier.domain.entities.user import User
from ml_classifier.domain.repositories.user_repository import UserRepository
from ml_classifier.models.admin import AdminUserFilter
from ml_classifier.services.admin_user_use_case import AdminUserUseCase


@pytest.fixture
def mock_user_repository():
    """Fixture to create a mock user repository."""
    repo = AsyncMock(spec=UserRepository)
    return repo


@pytest.fixture
def admin_use_case(mock_user_repository):
    """Fixture to create an AdminUserUseCase instance."""
    return AdminUserUseCase(mock_user_repository)


@pytest.fixture
def sample_users():
    """Fixture to create sample users for testing."""
    user1 = User(
        id=uuid.uuid4(),
        email="user1@example.com",
        hashed_password="hashed_password",
        full_name="User One",
        is_active=True,
        is_admin=False,
        balance=Decimal("100.00"),
    )

    user2 = User(
        id=uuid.uuid4(),
        email="user2@example.com",
        hashed_password="hashed_password",
        full_name="User Two",
        is_active=False,
        is_admin=False,
        balance=Decimal("50.00"),
    )

    admin = User(
        id=uuid.uuid4(),
        email="admin@example.com",
        hashed_password="hashed_password",
        full_name="Admin User",
        is_active=True,
        is_admin=True,
        balance=Decimal("500.00"),
    )

    return [user1, user2, admin]


class TestAdminUserUseCase:
    """Tests for AdminUserUseCase functionality."""

    @pytest.mark.asyncio
    async def test_list_users_no_filters(
        self, admin_use_case, mock_user_repository, sample_users
    ):
        """Test listing users without filters."""
        # Setup
        mock_user_repository.list.return_value = sample_users
        mock_user_repository.count.return_value = len(sample_users)

        # Execute
        filters = AdminUserFilter()
        users, count = await admin_use_case.list_users(filters)

        # Assert
        assert len(users) == len(sample_users)
        assert count == len(sample_users)
        mock_user_repository.list.assert_called_once()
        mock_user_repository.count.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_users_with_search(
        self, admin_use_case, mock_user_repository, sample_users
    ):
        """Test listing users with search filter."""
        # Setup - we'll mimic the in-memory filtering by returning all users
        mock_user_repository.list.return_value = sample_users
        mock_user_repository.count.return_value = len(sample_users)

        # Execute - should only match "User One"
        filters = AdminUserFilter(search="one")
        users, count = await admin_use_case.list_users(filters)

        # Assert - our in-memory filtering should reduce to 1 user
        assert len(users) == 1
        assert users[0].full_name == "User One"

    @pytest.mark.asyncio
    async def test_list_users_with_active_filter(
        self, admin_use_case, mock_user_repository, sample_users
    ):
        """Test listing users with active status filter."""
        # Setup - we'll mimic the in-memory filtering by returning all users
        mock_user_repository.list.return_value = sample_users
        mock_user_repository.count.return_value = len(sample_users)

        # Execute - filter active users
        filters = AdminUserFilter(is_active=True)
        users, count = await admin_use_case.list_users(filters)

        # Assert - should get 2 active users (user1 and admin)
        assert len(users) == 2
        assert all(user.is_active for user in users)

    @pytest.mark.asyncio
    async def test_get_user(self, admin_use_case, mock_user_repository, sample_users):
        """Test getting a user by ID."""
        # Setup
        user_id = sample_users[0].id
        mock_user_repository.get_by_id.return_value = sample_users[0]

        # Execute
        user = await admin_use_case.get_user(user_id)

        # Assert
        assert user is not None
        assert user.id == user_id
        mock_user_repository.get_by_id.assert_called_once_with(user_id)

    @pytest.mark.asyncio
    async def test_update_user_status_activate(
        self, admin_use_case, mock_user_repository, sample_users
    ):
        """Test activating a user."""
        # Setup - use inactive user
        user = sample_users[1]
        mock_user_repository.get_by_id.return_value = user

        # The update should create a new user object with is_active=True
        def side_effect(updated_user):
            assert updated_user.is_active is True
            return updated_user

        mock_user_repository.update.side_effect = side_effect

        # Execute
        success, message, updated = await admin_use_case.update_user_status(
            user.id, True
        )

        # Assert
        assert success is True
        assert "activated" in message.lower()
        assert updated is not None
        mock_user_repository.get_by_id.assert_called_once()
        mock_user_repository.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_admin_status(
        self, admin_use_case, mock_user_repository, sample_users
    ):
        """Test setting admin status."""
        # Setup - use regular user
        user = sample_users[0]
        mock_user_repository.get_by_id.return_value = user

        # The update should create a new user object with is_admin=True
        def side_effect(updated_user):
            assert updated_user.is_admin is True
            return updated_user

        mock_user_repository.update.side_effect = side_effect

        # Execute
        success, message, updated = await admin_use_case.set_admin_status(user.id, True)

        # Assert
        assert success is True
        assert "granted admin" in message.lower()
        assert updated is not None
        mock_user_repository.get_by_id.assert_called_once()
        mock_user_repository.update.assert_called_once()
