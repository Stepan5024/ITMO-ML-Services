"""Integration tests for admin API endpoints."""
import uuid

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from unittest.mock import patch, AsyncMock, MagicMock

from ml_classifier.controller.admin_user_controller import router as admin_router
from ml_classifier.models.admin import AdminUserFilter


@pytest.fixture
def app():
    """Create a test FastAPI application."""
    app = FastAPI()
    app.include_router(admin_router)
    return app


@pytest_asyncio.fixture
async def async_client(app):
    """Create an async test client."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client


@pytest.fixture
def admin_token():
    """Create a valid admin JWT token."""
    import uuid
    from ml_classifier.infrastructure.security.jwt import create_access_token

    return create_access_token(
        subject=uuid.uuid4(), email="admin@example.com", is_admin=True
    )


@pytest.fixture
def regular_token():
    """Create a regular user JWT token."""
    import uuid
    from ml_classifier.infrastructure.security.jwt import create_access_token

    return create_access_token(
        subject=uuid.uuid4(), email="user@example.com", is_admin=False
    )


@pytest.fixture
def sample_users():
    """Create sample users for testing."""
    return [
        MagicMock(
            id=uuid.uuid4(),
            email="user1@example.com",
            full_name="User One",
            is_active=True,
            is_admin=False,
            balance=100.0,
            created_at="2023-01-01T00:00:00Z",
            updated_at="2023-01-01T00:00:00Z",
        ),
        MagicMock(
            id=uuid.uuid4(),
            email="user2@example.com",
            full_name="User Two",
            is_active=False,
            is_admin=False,
            balance=50.0,
            created_at="2023-01-01T00:00:00Z",
            updated_at="2023-01-01T00:00:00Z",
        ),
    ]


@pytest.mark.asyncio
async def test_list_users_success(
    async_client, admin_token, sample_users, app: FastAPI
):
    """Test successfully listing users."""
    from ml_classifier.infrastructure.web.auth_middleware import get_current_user

    # Create a mock admin user with required attributes
    mock_admin_user = MagicMock(
        id=uuid.uuid4(),
        email="admin@example.com",
        full_name="Admin User",
        is_active=True,
        is_admin=True,
        balance=0.0,
        created_at="2023-01-01T00:00:00Z",
        updated_at="2023-01-01T00:00:00Z",
    )

    # Define a mock implementation for get_current_user
    async def mock_get_current_user_override():
        return mock_admin_user

    # Override the dependency in the FastAPI app
    app.dependency_overrides[get_current_user] = mock_get_current_user_override

    try:
        # Patch the permissions check
        with patch(
            "ml_classifier.controller.admin_user_controller.has_permission",
            return_value=True,
        ):
            # Patch the admin use case
            with patch(
                "ml_classifier.services.admin_user_use_case.AdminUserUseCase.list_users",
                new_callable=AsyncMock,
            ) as mock_list:
                mock_list.return_value = (sample_users, len(sample_users))

                # Execute request
                response = await async_client.get(
                    "/api/v1/admin/users",
                    headers={"Authorization": f"Bearer {admin_token}"},
                )

                # Assert
                assert response.status_code == 200
                data = response.json()
                assert len(data["items"]) == 2
                assert data["total"] == 2
                assert mock_list.called
                # Verify that filtering was passed correctly
                call_args = mock_list.call_args[0][0]
                assert isinstance(call_args, AdminUserFilter)
                assert call_args.page == 1
                assert call_args.size == 10
    finally:
        # Clean up dependency overrides
        app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_get_user_success(async_client, admin_token, sample_users, app: FastAPI):
    """Test successfully getting user details."""
    from ml_classifier.infrastructure.web.auth_middleware import get_current_user

    user_id = uuid.uuid4()

    # Create a mock admin user with required attributes
    mock_admin_user = MagicMock(
        id=uuid.uuid4(),
        email="admin@example.com",
        full_name="Admin User",
        is_active=True,
        is_admin=True,
        balance=0.0,
        created_at="2023-01-01T00:00:00Z",
        updated_at="2023-01-01T00:00:00Z",
    )

    # Define a mock implementation for get_current_user
    async def mock_get_current_user_override():
        return mock_admin_user

    # Override the dependency in the FastAPI app
    app.dependency_overrides[get_current_user] = mock_get_current_user_override

    try:
        # Patch the permissions check
        with patch(
            "ml_classifier.controller.admin_user_controller.has_permission",
            return_value=True,
        ):
            # Patch the admin use case
            with patch(
                "ml_classifier.services.admin_user_use_case.AdminUserUseCase.get_user",
                new_callable=AsyncMock,
            ) as mock_get:
                mock_get.return_value = sample_users[0]

                # Execute request
                response = await async_client.get(
                    f"/api/v1/admin/users/{user_id}",
                    headers={"Authorization": f"Bearer {admin_token}"},
                )

                # Assert
                assert response.status_code == 200
                data = response.json()
                assert data["email"] == sample_users[0].email
                assert data["full_name"] == sample_users[0].full_name
                mock_get.assert_called_once_with(user_id)
    finally:
        # Clean up dependency overrides
        app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_activate_user_success(
    async_client, admin_token, sample_users, app: FastAPI
):
    """Test successfully activating a user."""
    from ml_classifier.infrastructure.web.auth_middleware import get_current_user

    user_id = uuid.uuid4()

    # Create a mock admin user with required attributes
    mock_admin_user = MagicMock(
        id=uuid.uuid4(),
        email="admin@example.com",
        full_name="Admin User",
        is_active=True,
        is_admin=True,
        balance=0.0,
        created_at="2023-01-01T00:00:00Z",
        updated_at="2023-01-01T00:00:00Z",
    )

    # Define a mock implementation for get_current_user
    async def mock_get_current_user_override():
        return mock_admin_user

    # Override the dependency in the FastAPI app
    app.dependency_overrides[get_current_user] = mock_get_current_user_override

    try:
        with patch(
            "ml_classifier.controller.admin_user_controller.has_permission",
            return_value=True,
        ):
            with patch(
                "ml_classifier.services.admin_user_use_case.AdminUserUseCase.update_user_status",
                new_callable=AsyncMock,
            ) as mock_update:
                original_user = sample_users[1]
                activated_user = MagicMock(
                    id=original_user.id,
                    email=original_user.email,
                    full_name=original_user.full_name,
                    is_active=True,
                    is_admin=original_user.is_admin,
                    balance=original_user.balance,
                    created_at=original_user.created_at,
                    updated_at=original_user.updated_at,
                )
                mock_update.return_value = (
                    True,
                    "User has been activated",
                    activated_user,
                )

                # Execute request
                response = await async_client.post(
                    f"/api/v1/admin/users/{user_id}/activate",
                    headers={"Authorization": f"Bearer {admin_token}"},
                )

                # Assert
                assert response.status_code == 200
                data = response.json()
                assert data["is_active"] is True
                mock_update.assert_called_once_with(user_id, True)
    finally:
        app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_deactivate_user_success(
    async_client, admin_token, sample_users, app: FastAPI
):
    """Test successfully deactivating a user."""
    from ml_classifier.infrastructure.web.auth_middleware import get_current_user

    user_id = uuid.uuid4()

    mock_admin_user = MagicMock(
        id=uuid.uuid4(),
        email="admin@example.com",
        is_admin=True,
        is_active=True,
    )

    async def mock_get_current_user_override():
        return mock_admin_user

    app.dependency_overrides[get_current_user] = mock_get_current_user_override

    try:
        with patch(
            "ml_classifier.controller.admin_user_controller.has_permission",
            return_value=True,
        ):
            with patch(
                "ml_classifier.services.admin_user_use_case.AdminUserUseCase.update_user_status",
                new_callable=AsyncMock,
            ) as mock_update:
                deactivated_user = MagicMock(
                    **{**vars(sample_users[0]), "is_active": False}
                )
                mock_update.return_value = (True, "User deactivated", deactivated_user)

                response = await async_client.post(
                    f"/api/v1/admin/users/{user_id}/deactivate",
                    headers={"Authorization": f"Bearer {admin_token}"},
                )

                assert response.status_code == 200
                data = response.json()
                assert data["is_active"] is False
                mock_update.assert_called_once_with(user_id, False)
    finally:
        app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_set_admin_privileges(
    async_client, admin_token, sample_users, app: FastAPI
):
    """Test granting admin privileges to a regular user."""
    from ml_classifier.infrastructure.web.auth_middleware import get_current_user

    user_id = uuid.uuid4()

    mock_admin_user = MagicMock(
        id=uuid.uuid4(),
        email="admin@example.com",
        is_admin=True,
        is_active=True,
    )

    async def mock_get_current_user_override():
        return mock_admin_user

    app.dependency_overrides[get_current_user] = mock_get_current_user_override

    try:
        with patch(
            "ml_classifier.controller.admin_user_controller.has_permission",
            return_value=True,
        ):
            with patch(
                "ml_classifier.services.admin_user_use_case.AdminUserUseCase.set_admin_status",
                new_callable=AsyncMock,
            ) as mock_set_admin:
                admin_user = MagicMock(**{**vars(sample_users[0]), "is_admin": True})
                mock_set_admin.return_value = (
                    True,
                    "Admin privileges granted",
                    admin_user,
                )

                response = await async_client.post(
                    f"/api/v1/admin/users/{user_id}/admin-status",
                    headers={"Authorization": f"Bearer {admin_token}"},
                    json={"is_admin": True},
                )

                assert response.status_code == 200
                data = response.json()
                assert data["is_admin"] is True
                mock_set_admin.assert_called_once_with(user_id, True)
    finally:
        app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_admin_api_filtering_and_pagination(
    async_client, admin_token, app: FastAPI
):
    """Test user listing with multiple filter combinations and pagination."""
    from ml_classifier.infrastructure.web.auth_middleware import get_current_user

    mock_admin_user = MagicMock(
        id=uuid.uuid4(),
        email="admin@example.com",
        is_admin=True,
        is_active=True,
    )

    async def mock_get_current_user_override():
        return mock_admin_user

    app.dependency_overrides[get_current_user] = mock_get_current_user_override

    try:
        with patch(
            "ml_classifier.controller.admin_user_controller.has_permission",
            return_value=True,
        ):
            with patch(
                "ml_classifier.services.admin_user_use_case.AdminUserUseCase.list_users",
                new_callable=AsyncMock,
            ) as mock_list:
                # Исправленные тестовые кейсы
                test_cases = [
                    ({"search": "user1", "is_active": True}, 1),
                    ({"is_admin": False, "page": 2, "size": 5}, 3),
                    ({"is_active": False, "is_admin": False}, 2),  # Добавлен is_admin
                ]

                for filters, expected_total in test_cases:
                    mock_list.reset_mock()
                    mock_list.return_value = ([], expected_total)

                    response = await async_client.get(
                        "/api/v1/admin/users",
                        headers={"Authorization": f"Bearer {admin_token}"},
                        params=filters,
                    )

                    assert response.status_code == 200
                    data = response.json()
                    assert data["total"] == expected_total

                    # Проверка всех параметров фильтра
                    passed_filter = mock_list.call_args[0][0]
                    for key, value in filters.items():
                        assert getattr(passed_filter, key) == value, (
                            f"Filter parameter {key} mismatch. "
                            f"Expected: {value}, Actual: {getattr(passed_filter, key)}"
                        )
    finally:
        app.dependency_overrides = {}


@pytest.mark.parametrize(
    "method, url, json_data",
    [
        ("GET", "/api/v1/admin/users", None),
        ("GET", f"/api/v1/admin/users/{uuid.uuid4()}", None),
        ("POST", f"/api/v1/admin/users/{uuid.uuid4()}/activate", None),
        ("POST", f"/api/v1/admin/users/{uuid.uuid4()}/deactivate", None),
        (
            "POST",
            f"/api/v1/admin/users/{uuid.uuid4()}/admin-status",
            {"is_admin": True},
        ),
    ],
)
@pytest.mark.asyncio
async def test_unauthorized_access_to_admin_endpoints(
    async_client: AsyncClient,
    regular_token: str,
    app: FastAPI,
    method: str,
    url: str,
    json_data: dict | None,
) -> None:
    """Test that regular users cannot access admin endpoints."""
    from ml_classifier.infrastructure.web.auth_middleware import get_current_user

    # Mock regular user with correct attributes
    mock_regular_user = MagicMock(
        id=uuid.uuid4(),
        email="user@example.com",
        is_admin=False,
        is_active=True,
        balance=0.0,
        created_at="2023-01-01T00:00:00Z",
        updated_at="2023-01-01T00:00:00Z",
    )

    # Override auth dependency to return regular user
    async def mock_get_current_user_override():
        return mock_regular_user

    app.dependency_overrides[get_current_user] = mock_get_current_user_override

    try:
        # Make request to admin endpoint with regular user token
        kwargs = {"headers": {"Authorization": f"Bearer {regular_token}"}}
        if json_data is not None:
            kwargs["json"] = json_data

        if method == "GET":
            response = await async_client.get(url, **kwargs)
        elif method == "POST":
            response = await async_client.post(url, **kwargs)

        # Assert 403 Forbidden
        assert response.status_code == 403, f"Failed for {method} {url}"
        assert response.json()["detail"] == "Not enough permissions"
    finally:
        # Cleanup dependency override
        app.dependency_overrides = {}
