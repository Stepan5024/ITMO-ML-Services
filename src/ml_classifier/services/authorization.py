"""Сервис авторизации для проверки прав доступа пользователя."""

import logging
import time
from uuid import uuid4
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
    operation_id = str(uuid4())
    start_time = time.time()

    logger.info(
        f"[{operation_id}] Начало проверки роли: user_id={user.id}, email={user.email}, role={role.value}"
    )

    result = False
    if role == RoleType.ADMIN:
        result = user.is_admin
        logger.debug(
            f"[{operation_id}] Проверка прав администратора: user_id={user.id}, is_admin={user.is_admin}"
        )
    elif role == RoleType.USER:
        result = user.is_active
        logger.debug(
            f"[{operation_id}] Проверка активности пользователя: user_id={user.id}, is_active={user.is_active}"
        )

    execution_time = time.time() - start_time
    log_level = logging.INFO if result else logging.WARNING
    logger.log(
        log_level,
        f"[{operation_id}] Результат проверки роли: user_id={user.id}, role={role.value}, result={result} |"
        f" Время выполнения: {execution_time:.3f}с",
    )

    return result


def get_permissions_for_user(user: User) -> list[Permission]:
    """
    Возвращает список разрешений, доступных пользователю, исходя из его ролей.

    Args:
        user: Пользователь, для которого получаем разрешения.

    Returns:
        list[Permission]: Список разрешений пользователя.
    """
    operation_id = str(uuid4())
    start_time = time.time()

    logger.info(
        f"[{operation_id}] Запрос разрешений для пользователя: user_id={user.id}, email={user.email}, "
        f"is_admin={user.is_admin}, is_active={user.is_active}"
    )

    if user.is_admin:
        permissions = list(Permission)
        permission_names = [p.value for p in permissions]
        execution_time = time.time() - start_time
        logger.debug(
            f"[{operation_id}] Выданы права администратора: user_id={user.id}, количество разрешений={len(permissions)}"
            f" | Время выполнения: {execution_time:.3f}с"
        )
        logger.debug(f"[{operation_id}] Список прав администратора: {permission_names}")
        return permissions

    permissions = []
    if user.is_active:
        logger.debug(
            f"[{operation_id}] Пользователь активен, выдача стандартных прав: user_id={user.id}"
        )
        permissions.extend(
            [
                Permission.READ_USER,
                Permission.READ_MODEL,
                Permission.READ_TASK,
                Permission.WRITE_TASK,
                Permission.READ_TRANSACTION,
            ]
        )
    else:
        logger.warning(
            f"[{operation_id}] Пользователь не активен, права не выданы: user_id={user.id}"
        )

    permission_names = [p.value for p in permissions]
    execution_time = time.time() - start_time
    logger.debug(
        f"[{operation_id}] Права пользователя: user_id={user.id}, количество разрешений={len(permissions)}"
        f" | Время выполнения: {execution_time:.3f}с"
    )
    logger.debug(f"[{operation_id}] Список прав пользователя: {permission_names}")
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
    operation_id = str(uuid4())
    start_time = time.time()

    logger.info(
        f"[{operation_id}] Начало проверки разрешения: user_id={user.id}, email={user.email}, "
        f"permission={permission.value}"
    )

    permissions = get_permissions_for_user(user)
    result = permission in permissions

    execution_time = time.time() - start_time
    log_level = logging.INFO if result else logging.WARNING
    logger.log(
        log_level,
        f"[{operation_id}] Результат проверки разрешения: user_id={user.id}, "
        f"permission={permission.value}, result={result} | Время выполнения: {execution_time:.3f}с",
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
    operation_id = str(uuid4())
    start_time = time.time()

    logger.info(
        f"[{operation_id}] Проверка доступа к данным пользователя: requestor_id={user.id},"
        f" email={user.email}, target_user_id={target_user_id}"
    )

    # Проверяем доступ: либо пользователь запрашивает свои данные, либо это администратор
    is_self_access = str(user.id) == target_user_id
    is_admin_access = user.is_admin
    result = is_self_access or is_admin_access

    execution_time = time.time() - start_time

    if result:
        if is_self_access:
            logger.info(
                f"[{operation_id}] Доступ разрешен (собственные данные): user_id={user.id},"
                f" target_user_id={target_user_id} | Время выполнения: {execution_time:.3f}с"
            )
        else:
            logger.info(
                f"[{operation_id}] Доступ разрешен (админ): user_id={user.id}, "
                f"target_user_id={target_user_id} | Время выполнения: {execution_time:.3f}с"
            )
    else:
        logger.warning(
            f"[{operation_id}] Доступ запрещен: user_id={user.id}, target_user_id={target_user_id}"
            f" | Время выполнения: {execution_time:.3f}с"
        )

    return result
