"""Сервис авторизации для проверки прав доступа пользователя."""

import logging
from ml_classifier.domain.entities.role import Permission, RoleType
from ml_classifier.domain.entities.user import User

logger = logging.getLogger(__name__)


def has_role(user: User, role: RoleType) -> bool:
    """
    Проверяет, имеет ли пользователь указанную роль.

    Args:
        user: Пользователь, которого проверяем.
        role: Роль, наличие которой необходимо проверить.

    Returns:
        bool: True, если пользователь обладает указанной ролью.
    """
    result = False
    if role == RoleType.ADMIN:
        result = user.is_admin
    elif role == RoleType.USER:
        result = user.is_active

    logger.debug(f"Проверка роли: user_id={user.id}, role={role}, result={result}")
    return result


def get_permissions_for_user(user: User) -> list[Permission]:
    """
    Возвращает список разрешений, доступных пользователю, исходя из его ролей.

    Args:
        user: Пользователь, для которого получаем разрешения.

    Returns:
        list[Permission]: Список разрешений пользователя.
    """
    if user.is_admin:
        permissions = list(Permission)
        logger.debug(
            f"Права пользователя (админ): user_id={user.id}, permissions={permissions}"
        )
        return permissions

    permissions = []
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

    logger.debug(f"Права пользователя: user_id={user.id}, permissions={permissions}")
    return permissions


def has_permission(user: User, permission: Permission) -> bool:
    """
    Проверяет, имеет ли пользователь указанное разрешение.

    Args:
        user: Пользователь, которого проверяем.
        permission: Разрешение, которое необходимо проверить.

    Returns:
        bool: True, если пользователь обладает данным разрешением.
    """
    permissions = get_permissions_for_user(user)
    result = permission in permissions
    logger.debug(
        f"Проверка разрешения: user_id={user.id}, permission={permission}, result={result}"
    )
    return result


def can_access_user_data(user: User, target_user_id: str) -> bool:
    """
    Проверяет, может ли пользователь получить доступ к данным другого пользователя.

    Args:
        user: Пользователь, запрашивающий доступ.
        target_user_id: ID пользователя, к чьим данным осуществляется доступ.

    Returns:
        bool: True, если доступ разрешён.
    """
    result = str(user.id) == target_user_id or user.is_admin
    logger.debug(
        f"Проверка доступа к данным пользователя: user_id={user.id}, target_user_id={target_user_id}, result={result}"
    )
    return result
