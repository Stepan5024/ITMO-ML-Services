"""Integration tests for authentication API endpoints."""
import pytest_asyncio
import uuid
from unittest.mock import patch, AsyncMock, MagicMock
from httpx import ASGITransport
import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI
from httpx import AsyncClient

from ml_classifier.controller.auth_controller import router as auth_router
from ml_classifier.infrastructure.security.jwt import create_access_token


@pytest.fixture
def app():
    """Create a test FastAPI application."""
    app = FastAPI()
    app.include_router(auth_router)
    return app


@pytest.fixture
def client(app):
    """Create a test client."""
    return TestClient(app)


@pytest_asyncio.fixture
async def async_client(app):
    """Create an async test client."""
    async with AsyncClient(
        transport=ASGITransport(app=app),  # Используйте transport вместо app
        base_url="http://test",
    ) as client:
        yield client


@pytest.fixture
def test_user():
    """Create a test user data."""
    return {
        "email": "test@example.com",
        "password": "StrongPass123",
        "full_name": "Test User",
    }


@pytest.fixture
def test_admin():
    """Create a test admin data."""
    return {
        "email": "admin@example.com",
        "password": "AdminPass123",
        "full_name": "Admin User",
        "is_admin": True,
    }


@pytest.fixture
def valid_token():
    """Create a valid JWT token."""
    import uuid

    return create_access_token(subject=uuid.uuid4(), email="test@example.com")


@pytest.fixture
def admin_token():
    """Create a valid admin JWT token."""
    import uuid

    return create_access_token(
        subject=uuid.uuid4(), email="admin@example.com", is_admin=True
    )


@pytest.fixture
def expired_token():
    """Create an expired JWT token."""
    import uuid
    import datetime
    from jose import jwt
    from ml_classifier.config.security import JWT_ALGORITHM, JWT_SECRET_KEY

    expire = datetime.datetime.utcnow() - datetime.timedelta(minutes=15)
    to_encode = {
        "sub": str(uuid.uuid4()),
        "email": "test@example.com",
        "exp": expire,
    }
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


@pytest.mark.asyncio
async def test_register_user_success(async_client, test_user):
    """Test successful user registration."""
    # Setup: Mock user_use_case to return successful registration
    with patch(
        "ml_classifier.services.user_use_cases.UserUseCase.register_user",
        new_callable=AsyncMock,
    ) as mock_register:
        mock_register.return_value = (
            True,
            "User registered successfully",
            MagicMock(
                id=uuid.uuid4(),
                email=test_user["email"],
                full_name=test_user["full_name"],
                is_active=True,
                is_admin=False,
                balance=0.0,
            ),
        )

        # Execute
        response = await async_client.post("/api/v1/auth/register", json=test_user)

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == test_user["email"]
        assert data["full_name"] == test_user["full_name"]
        assert "id" in data
        mock_register.assert_called_once()


@pytest.mark.asyncio
async def test_register_user_duplicate_email(async_client, test_user):
    """Test user registration with duplicate email."""
    # Setup: Mock user_use_case to return failed registration due to duplicate email
    with patch(
        "ml_classifier.services.user_use_cases.UserUseCase.register_user",
        new_callable=AsyncMock,
    ) as mock_register:
        mock_register.return_value = (
            False,
            f"Email {test_user['email']} is already registered.",
            None,
        )

        # Execute
        response = await async_client.post("/api/v1/auth/register", json=test_user)

        # Assert
        assert response.status_code == 400
        data = response.json()
        assert "already registered" in data["detail"].lower()
        mock_register.assert_called_once()


@pytest.mark.asyncio
async def test_register_user_weak_password(async_client, test_user):
    """Test user registration with weak password."""
    weak_user = test_user.copy()
    weak_user["password"] = "weak"

    # Убрали мок, так как ошибка возникает на уровне Pydantic валидации
    response = await async_client.post("/api/v1/auth/register", json=weak_user)

    assert response.status_code == 422
    data = response.json()

    # Правильная проверка структуры ошибки
    assert any(error["loc"] == ["body", "password"] for error in data["detail"])
    assert any(
        "at least 8 characters" in error["msg"].lower() for error in data["detail"]
    )


@pytest.mark.asyncio
async def test_login_success(async_client, test_user):
    """Test successful login."""
    # Setup: Mock authenticate_user to return a user
    with patch(
        "ml_classifier.services.user_use_cases.UserUseCase.authenticate_user",
        new_callable=AsyncMock,
    ) as mock_auth:
        mock_auth.return_value = MagicMock(
            id=uuid.uuid4(),
            email=test_user["email"],
            is_active=True,
            is_admin=False,
        )

        # Execute - use OAuth2 form data format
        response = await async_client.post(
            "/api/v1/auth/login",
            data={
                "username": test_user["email"],
                "password": test_user["password"],
            },
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        mock_auth.assert_called_once()


@pytest.mark.asyncio
async def test_login_invalid_credentials(async_client, test_user):
    """Test login with invalid credentials."""
    # Setup: Mock authenticate_user to return None (auth failure)
    with patch(
        "ml_classifier.services.user_use_cases.UserUseCase.authenticate_user",
        new_callable=AsyncMock,
    ) as mock_auth:
        mock_auth.return_value = None

        # Execute
        response = await async_client.post(
            "/api/v1/auth/login",
            data={
                "username": test_user["email"],
                "password": "WrongPassword123",
            },
        )

        # Assert
        assert response.status_code == 401
        data = response.json()
        assert "incorrect" in data["detail"].lower()
        mock_auth.assert_called_once()


@pytest.mark.asyncio
async def test_me_endpoint_valid_token(async_client, valid_token):
    """Test accessing /me endpoint with valid token."""
    # First, patch the get_user_by_id method in UserUseCase to prevent DB access
    with patch(
        "ml_classifier.services.user_use_cases.UserUseCase.get_user_by_id",
        new_callable=AsyncMock,
    ) as mock_get_user_by_id:
        # Setup user that will be returned directly
        test_user = MagicMock(
            id=uuid.uuid4(),
            email="test@example.com",
            full_name="Test User",
            is_active=True,
            is_admin=False,
            balance=100.0,
        )

        # Set up the mock to return our test user
        mock_get_user_by_id.return_value = test_user

        # Execute request with authorization header
        response = await async_client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {valid_token}"}
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "test@example.com"
        assert data["full_name"] == "Test User"
        assert data["balance"] == 100.0
        assert mock_get_user_by_id.called


@pytest.mark.asyncio
async def test_me_endpoint_no_token(async_client):
    """Test accessing /me endpoint without token."""
    response = await async_client.get("/api/v1/auth/me")
    assert response.status_code == 401
    data = response.json()
    assert "not authenticated" in data["detail"].lower()


@pytest.mark.asyncio
async def test_change_password_success(async_client, valid_token):
    """Test successful password change."""
    # Mock get_user_by_id to prevent database access
    with patch(
        "ml_classifier.services.user_use_cases.UserUseCase.get_user_by_id",
        new_callable=AsyncMock,
    ) as mock_get_user_by_id:
        # Create a mock user
        mock_user = MagicMock(id=uuid.uuid4())
        mock_get_user_by_id.return_value = mock_user

        # Now mock change_password
        with patch(
            "ml_classifier.services.user_use_cases.UserUseCase.change_password",
            new_callable=AsyncMock,
        ) as mock_change_pwd:
            mock_change_pwd.return_value = (True, "Password updated successfully")

            # Execute
            response = await async_client.post(
                "/api/v1/auth/change-password",
                json={
                    "current_password": "OldPass123",
                    "new_password": "NewStrongPass123",
                },
                headers={"Authorization": f"Bearer {valid_token}"},
            )

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert "success" in data["message"].lower()
            # Verify mocks were called
            assert mock_get_user_by_id.called
            mock_change_pwd.assert_called_once()
