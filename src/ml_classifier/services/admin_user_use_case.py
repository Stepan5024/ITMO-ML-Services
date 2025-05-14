"""
Администрирование пользователей — use case-слой.

Реализует бизнес-логику управления пользователями:
- Просмотр списка пользователей с фильтрами
- Получение пользователя по ID
- Изменение статуса активности
- Назначение/снятие прав администратора
"""

import logging
from datetime import datetime
from typing import List, Optional, Tuple
from uuid import UUID

from fastapi import Depends

from ml_classifier.domain.entities.user import User
from ml_classifier.domain.repositories.user_repository import UserRepository
from ml_classifier.infrastructure.db.database import get_db
from ml_classifier.infrastructure.db.repositories.user_repository import (
    SQLAlchemyUserRepository,
)
from ml_classifier.models.admin import AdminUserFilter

logger = logging.getLogger(__name__)


class AdminUserUseCase:
    """
    Use Case для операций администрирования пользователей.
    """

    def __init__(self, user_repository: UserRepository):
        """
        Инициализация с репозиторием пользователей.

        :param user_repository: Репозиторий пользователей
        """
        self.user_repository = user_repository

    async def list_users(self, filters: AdminUserFilter) -> Tuple[List[User], int]:
        """
        Получить список пользователей с возможностью фильтрации и пагинации.

        :param filters: Критерии фильтрации
        :return: Список пользователей и общее количество после фильтрации
        """
        offset = (filters.page - 1) * filters.size
        logger.debug(
            f"Получение списка пользователей: offset={offset}, size={filters.size}"
        )

        all_users = await self.user_repository.list(skip=offset, limit=filters.size)

        filtered_users = []
        for user in all_users:
            if filters.search:
                search_term = filters.search.lower()
                if not (
                    (user.email and search_term in user.email.lower())
                    or (user.full_name and search_term in user.full_name.lower())
                ):
                    continue

            if filters.is_active is not None and user.is_active != filters.is_active:
                continue

            if filters.is_admin is not None and user.is_admin != filters.is_admin:
                continue

            filtered_users.append(user)

        filtered_count = len(filtered_users)
        logger.info(f"Найдено пользователей после фильтрации: {filtered_count}")
        return filtered_users, filtered_count

    async def get_user(self, user_id: UUID) -> Optional[User]:
        """
        Получить пользователя по ID.

        :param user_id: Идентификатор пользователя
        :return: Пользователь, если найден
        """
        logger.debug(f"Запрос пользователя по ID: {user_id}")
        user = await self.user_repository.get_by_id(user_id)
        if user:
            logger.info(f"Пользователь найден: {user.email}")
        else:
            logger.warning(f"Пользователь не найден: {user_id}")
        return user

    async def update_user_status(
        self, user_id: UUID, is_active: bool
    ) -> Tuple[bool, str, Optional[User]]:
        """
        Изменить статус активности пользователя.

        :param user_id: Идентификатор пользователя
        :param is_active: Новый статус активности (True/False)
        :return: Успех, сообщение, обновлённый пользователь
        """
        logger.info(
            f"Изменение статуса активности пользователя {user_id} -> {is_active}"
        )
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            logger.warning(f"Пользователь не найден: {user_id}")
            return False, f"Пользователь с ID {user_id} не найден", None

        updated_user = User(
            id=user.id,
            email=user.email,
            hashed_password=user.hashed_password,
            full_name=user.full_name,
            balance=user.balance,
            is_active=is_active,
            is_admin=user.is_admin,
            created_at=user.created_at,
            updated_at=datetime.utcnow(),
        )

        try:
            result = await self.user_repository.update(updated_user)
            status_str = "активирован" if is_active else "деактивирован"
            logger.info(f"Пользователь {user_id} был {status_str}")
            return True, f"Пользователь был {status_str}", result
        except Exception as e:
            logger.exception(
                f"Ошибка при обновлении статуса активности пользователя {user_id}: {e}"
            )
            return False, f"Ошибка при обновлении: {str(e)}", None

    async def set_admin_status(
        self, user_id: UUID, is_admin: bool
    ) -> Tuple[bool, str, Optional[User]]:
        """
        Назначить или снять права администратора у пользователя.

        :param user_id: Идентификатор пользователя
        :param is_admin: Новый статус администратора (True/False)
        :return: Успех, сообщение, обновлённый пользователь
        """
        logger.info(
            f"Изменение прав администратора пользователя {user_id} -> {is_admin}"
        )
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            logger.warning(f"Пользователь не найден: {user_id}")
            return False, f"Пользователь с ID {user_id} не найден", None

        updated_user = User(
            id=user.id,
            email=user.email,
            hashed_password=user.hashed_password,
            full_name=user.full_name,
            balance=user.balance,
            is_active=user.is_active,
            is_admin=is_admin,
            created_at=user.created_at,
            updated_at=datetime.utcnow(),
        )

        try:
            result = await self.user_repository.update(updated_user)
            status_str = (
                "назначен администратором" if is_admin else "лишён прав администратора"
            )
            logger.info(f"Пользователь {user_id} был {status_str}")
            return True, f"Пользователь был {status_str}", result
        except Exception as e:
            logger.exception(
                f"Ошибка при изменении прав администратора пользователя {user_id}: {e}"
            )
            return False, f"Ошибка при обновлении: {str(e)}", None


async def get_admin_user_repository(session=Depends(get_db)) -> UserRepository:
    """
    Зависимость для получения реализации репозитория пользователей.

    :param session: Сессия базы данных
    :return: Экземпляр репозитория пользователей
    """
    return SQLAlchemyUserRepository(session)


def get_admin_user_use_case(
    user_repo: UserRepository = Depends(get_admin_user_repository),
) -> AdminUserUseCase:
    """
    Зависимость для получения экземпляра AdminUserUseCase.

    :param user_repo: Репозиторий пользователей
    :return: Use Case для администрирования пользователей
    """
    return AdminUserUseCase(user_repo)
