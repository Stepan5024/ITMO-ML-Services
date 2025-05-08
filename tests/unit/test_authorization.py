"""Unit tests for authorization module."""
import uuid
from decimal import Decimal

import pytest

from ml_classifier.domain.entities.role import Permission, RoleType
from ml_classifier.domain.entities.user import User
from ml_classifier.services.authorization import (
    has_role,
    get_permissions_for_user,
    can_access_user_data,
)


@pytest.fixture
def regular_user() -> User:
    """Create a regular user for testing."""
    return User(
        id=uuid.uuid4(),
        email="user@example.com",
        hashed_password="hashed_password",
        full_name="Regular User",
        is_active=True,
        is_admin=False,
        balance=Decimal("100.00"),
    )


@pytest.fixture
def admin_user() -> User:
    """Create an admin user for testing."""
    return User(
        id=uuid.uuid4(),
        email="admin@example.com",
        hashed_password="hashed_password",
        full_name="Admin User",
        is_active=True,
        is_admin=True,
        balance=Decimal("500.00"),
    )


def test_has_role_regular_user(regular_user):
    """Test has_role function with regular user."""
    assert has_role(regular_user, RoleType.USER) is True
    assert has_role(regular_user, RoleType.ADMIN) is False


def test_has_role_admin_user(admin_user):
    """Test has_role function with admin user."""
    assert has_role(admin_user, RoleType.USER) is True
    assert has_role(admin_user, RoleType.ADMIN) is True


def test_get_permissions_regular_user(regular_user):
    """Test get_permissions_for_user with regular user."""
    permissions = get_permissions_for_user(regular_user)

    # Regular user should have these permissions
    assert Permission.READ_USER in permissions
    assert Permission.READ_MODEL in permissions
    assert Permission.READ_TASK in permissions
    assert Permission.WRITE_TASK in permissions

    # Regular user should not have these permissions
    assert Permission.WRITE_USER not in permissions
    assert Permission.DELETE_USER not in permissions


def test_get_permissions_admin_user(admin_user):
    """Test get_permissions_for_user with admin user."""
    permissions = get_permissions_for_user(admin_user)

    # Admin should have all permissions
    for perm in Permission:
        assert perm in permissions


def test_can_access_user_data(regular_user, admin_user):
    """Test can_access_user_data function."""
    # User can access their own data
    assert can_access_user_data(regular_user, str(regular_user.id)) is True

    # User cannot access another user's data
    assert can_access_user_data(regular_user, str(uuid.uuid4())) is False

    # Admin can access any user's data
    assert can_access_user_data(admin_user, str(regular_user.id)) is True
    assert can_access_user_data(admin_user, str(uuid.uuid4())) is True
