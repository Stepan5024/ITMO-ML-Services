"""Admin user management API controller."""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ml_classifier.domain.entities.role import Permission
from ml_classifier.domain.entities.user import User
from ml_classifier.infrastructure.web.auth_middleware import get_current_active_user
from ml_classifier.models.admin import (
    AdminUserFilter,
    AdminUserListResponse,
    AdminUserResponse,
    UserStatusUpdate,
)
from ml_classifier.services.admin_user_use_case import (
    AdminUserUseCase,
    get_admin_user_use_case,
)
from ml_classifier.services.authorization import has_permission

router = APIRouter(prefix="/api/v1/admin/users", tags=["admin"])


async def check_admin_permissions(
    current_user: User = Depends(get_current_active_user),
):
    """Check if current user has admin permissions."""
    if (
        not has_permission(current_user, Permission.READ_USER)
        or not current_user.is_admin
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    return current_user


@router.get("", response_model=AdminUserListResponse)
async def list_users(
    search: Optional[str] = Query(None, description="Search by email or full name"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    is_admin: Optional[bool] = Query(None, description="Filter by admin status"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Page size"),
    admin_user: User = Depends(check_admin_permissions),
    admin_use_case: AdminUserUseCase = Depends(get_admin_user_use_case),
):
    """
    Get a list of users with filtering and pagination.

    Args:
        search: Search term for email or full name
        is_active: Filter by active status
        page: Page number (starts at 1)
        size: Number of items per page
        admin_user: Admin user making the request
        admin_use_case: Admin use case dependency

    Returns:
        AdminUserListResponse: Paginated list of users
    """
    filters = AdminUserFilter(
        search=search,
        is_active=is_active,
        is_admin=is_admin,
        page=page,
        size=size,
    )

    users, total = await admin_use_case.list_users(filters)

    total_pages = (total + size - 1) // size  # Calculate total pages

    return AdminUserListResponse(
        items=[
            AdminUserResponse(
                id=user.id,
                email=user.email,
                full_name=user.full_name,
                is_active=user.is_active,
                is_admin=user.is_admin,
                balance=float(user.balance),
                created_at=user.created_at,
                updated_at=user.updated_at,
            )
            for user in users
        ],
        total=total,
        page=page,
        size=size,
        pages=total_pages,
    )


@router.get("/{user_id}", response_model=AdminUserResponse)
async def get_user(
    user_id: uuid.UUID,
    admin_user: User = Depends(check_admin_permissions),
    admin_use_case: AdminUserUseCase = Depends(get_admin_user_use_case),
):
    """
    Get detailed information about a specific user.

    Args:
        user_id: ID of the user to retrieve
        admin_user: Admin user making the request
        admin_use_case: Admin use case dependency

    Returns:
        AdminUserResponse: User details
    """
    user = await admin_use_case.get_user(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found",
        )

    return AdminUserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        is_admin=user.is_admin,
        balance=float(user.balance),
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


@router.post("/{user_id}/activate", response_model=AdminUserResponse)
async def activate_user(
    user_id: uuid.UUID,
    admin_user: User = Depends(check_admin_permissions),
    admin_use_case: AdminUserUseCase = Depends(get_admin_user_use_case),
):
    """
    Activate a user account.

    Args:
        user_id: ID of the user to activate
        admin_user: Admin user making the request
        admin_use_case: Admin use case dependency

    Returns:
        AdminUserResponse: Updated user details
    """
    success, message, user = await admin_use_case.update_user_status(user_id, True)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message,
        )

    return AdminUserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        is_admin=user.is_admin,
        balance=float(user.balance),
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


@router.post("/{user_id}/deactivate", response_model=AdminUserResponse)
async def deactivate_user(
    user_id: uuid.UUID,
    admin_user: User = Depends(check_admin_permissions),
    admin_use_case: AdminUserUseCase = Depends(get_admin_user_use_case),
):
    """
    Deactivate a user account.

    Args:
        user_id: ID of the user to deactivate
        admin_user: Admin user making the request
        admin_use_case: Admin use case dependency

    Returns:
        AdminUserResponse: Updated user details
    """
    success, message, user = await admin_use_case.update_user_status(user_id, False)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message,
        )

    return AdminUserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        is_admin=user.is_admin,
        balance=float(user.balance),
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


@router.post("/{user_id}/admin-status", response_model=AdminUserResponse)
async def set_admin_status(
    user_id: uuid.UUID,
    status_update: UserStatusUpdate,
    admin_user: User = Depends(check_admin_permissions),
    admin_use_case: AdminUserUseCase = Depends(get_admin_user_use_case),
):
    """
    Set a user's admin status.

    Args:
        user_id: ID of the user to update
        status_update: New admin status
        admin_user: Admin user making the request
        admin_use_case: Admin use case dependency

    Returns:
        AdminUserResponse: Updated user details
    """
    success, message, user = await admin_use_case.set_admin_status(
        user_id, status_update.is_admin
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message,
        )

    return AdminUserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        is_admin=user.is_admin,
        balance=float(user.balance),
        created_at=user.created_at,
        updated_at=user.updated_at,
    )
