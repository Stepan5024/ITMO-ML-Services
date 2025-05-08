"""Репозиторий для работы с пользователями."""
from abc import abstractmethod
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from ml_classifier.domain.entities import User
from ml_classifier.domain.repositories.base import Repository


class UserRepository(Repository[User]):
    """Интерфейс репозитория для работы с пользователями."""

    @abstractmethod
    async def get_by_email(self, email: str) -> Optional[User]:
        """Получить пользователя по email.

        Args:
            email: Email пользователя

        Returns:
            Optional[User]: Найденный пользователь или None
        """
        raise NotImplementedError

    @abstractmethod
    async def update_balance(self, user_id: UUID, amount: Decimal) -> User:
        """Обновить баланс пользователя.

        Args:
            user_id: Идентификатор пользователя
            amount: Сумма для добавления/вычитания (может быть отрицательной)

        Returns:
            User: Обновленный пользователь
        """
        raise NotImplementedError

    @abstractmethod
    async def get_active_users(self) -> List[User]:
        """Get all active users.

        Returns:
            List[User]: List of active users
        """
        raise NotImplementedError

    @abstractmethod
    async def get_admins(self) -> List[User]:
        """Get all admin users.

        Returns:
            List[User]: List of admin users
        """
        raise NotImplementedError
