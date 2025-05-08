"""Authorization service for checking user permissions."""

from ml_classifier.domain.entities.role import Permission, RoleType
from ml_classifier.domain.entities.user import User


def has_role(user: User, role: RoleType) -> bool:
    """
    Check if a user has a specific role.

    Args:
        user: User to check
        role: Role to check for

    Returns:
        bool: True if user has the role
    """
    if role == RoleType.ADMIN:
        return user.is_admin
    elif role == RoleType.USER:
        return user.is_active
    return False


def get_permissions_for_user(user: User) -> list[Permission]:
    """
    Get all permissions for a user based on their roles.

    Args:
        user: User to get permissions for

    Returns:
        list[Permission]: List of permissions
    """
    permissions = []

    if user.is_admin:
        return list(Permission)

    if user.is_active:
        permissions.extend(
            [
                Permission.READ_USER,
                Permission.READ_MODEL,
                Permission.READ_TASK,
                Permission.WRITE_TASK,
                Permission.READ_TRANSACTION,
            ]
        )

    return permissions


def has_permission(user: User, permission: Permission) -> bool:
    """
    Check if a user has a specific permission.

    Args:
        user: User to check
        permission: Permission to check for

    Returns:
        bool: True if user has the permission
    """
    permissions = get_permissions_for_user(user)
    return permission in permissions


def can_access_user_data(user: User, target_user_id: str) -> bool:
    """
    Check if a user can access another user's data.

    Args:
        user: User attempting to access data
        target_user_id: ID of the user whose data is being accessed

    Returns:
        bool: True if access is allowed
    """
    if str(user.id) == target_user_id:
        return True

    if user.is_admin:
        return True

    return False
