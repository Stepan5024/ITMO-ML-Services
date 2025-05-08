"""Integration tests for profile API endpoints."""
import datetime
import uuid
from decimal import Decimal
from ml_classifier.domain.entities.user import User
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, MagicMock

from ml_classifier.controller.profile_controller import router as profile_router
from fastapi import FastAPI


@pytest.fixture
def app():
    """Create a test FastAPI application."""
    app = FastAPI()
    app.include_router(profile_router)
    return app


@pytest_asyncio.fixture
async def async_client(app):
    """Create an async test client."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client


@pytest.fixture
def valid_token():
    """Create a valid JWT token."""
    import uuid
    from ml_classifier.infrastructure.security.jwt import create_access_token

    return create_access_token(subject=uuid.uuid4(), email="test@example.com")


@pytest.mark.asyncio
async def test_get_profile_success(async_client, valid_token, app):
    """Test successfully getting user profile."""
    import uuid
    from ml_classifier.infrastructure.web.auth_middleware import get_current_active_user

    # Setup mock user for the auth dependency
    mock_user = MagicMock(
        id=uuid.uuid4(),
        email="test@example.com",
        full_name="Test User",
        balance=100.0,
        is_active=True,
        is_admin=False,
        created_at="2023-01-01T00:00:00Z",
        updated_at="2023-01-01T00:00:00Z",
    )

    # Override the get_current_active_user dependency
    async def mock_get_current_active_user():
        return mock_user

    app.dependency_overrides[get_current_active_user] = mock_get_current_active_user

    try:
        # Execute request with authorization header
        response = await async_client.get(
            "/api/v1/profile", headers={"Authorization": f"Bearer {valid_token}"}
        )

        # Assert the response status code and data
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "test@example.com"
        assert data["full_name"] == "Test User"
        assert data["balance"] == 100.0
    finally:
        # Reset the dependency overrides after the test
        app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_update_profile_success(async_client, valid_token, app):
    """Test successfully updating user profile."""
    from ml_classifier.infrastructure.web.auth_middleware import get_current_active_user
    from ml_classifier.services.user_use_cases import UserUseCase, get_user_use_case

    # Create real User entity
    user_id = uuid.uuid4()
    test_user = User(
        id=user_id,
        email="test@example.com",
        hashed_password="hashed_password",
        full_name="Test User",
        is_active=True,
        is_admin=False,
        balance=Decimal("100.0"),
        created_at=datetime.datetime.utcnow(),
        updated_at=datetime.datetime.utcnow(),
    )

    updated_user = User(
        id=user_id,
        email="test@example.com",
        hashed_password="hashed_password",
        full_name="Updated Name",
        is_active=True,
        is_admin=False,
        balance=Decimal("100.0"),
        created_at=datetime.datetime.utcnow(),
        updated_at=datetime.datetime.utcnow(),
    )

    # Create mock user use case
    mock_user_use_case = AsyncMock(spec=UserUseCase)
    mock_user_use_case.update_user.return_value = (
        True,
        "User updated successfully",
        updated_user,
    )

    # Override dependencies
    async def mock_get_current_active_user():
        return test_user

    async def mock_get_user_use_case():
        return mock_user_use_case

    app.dependency_overrides[get_current_active_user] = mock_get_current_active_user
    app.dependency_overrides[get_user_use_case] = mock_get_user_use_case

    try:
        # Execute request
        response = await async_client.patch(
            "/api/v1/profile",
            headers={"Authorization": f"Bearer {valid_token}"},
            json={"full_name": "Updated Name"},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == "Updated Name"
        assert data["email"] == "test@example.com"

        # Check that the update_user method was called with the correct arguments
        mock_user_use_case.update_user.assert_awaited_once_with(
            test_user.id, full_name="Updated Name"
        )
    finally:
        app.dependency_overrides = {}
