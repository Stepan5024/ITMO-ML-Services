"""Базовый класс репозитория."""
from abc import ABC, abstractmethod
from typing import Generic, List, Optional, TypeVar
from uuid import UUID

from ml_classifier.domain.entities import Entity

T = TypeVar("T", bound=Entity)


class Repository(Generic[T], ABC):
    """Абстрактный базовый класс для всех репозиториев."""

    @abstractmethod
    async def get_by_id(self, entity_id: UUID) -> Optional[T]:
        """Получить сущность по ID.

        Args:
            entity_id: Идентификатор сущности

        Returns:
            Optional[T]: Найденная сущность или None
        """
        raise NotImplementedError

    @abstractmethod
    async def list(self, skip: int = 0, limit: int = 100) -> List[T]:
        """Получить список сущностей с пагинацией.

        Args:
            skip: Количество пропускаемых записей
            limit: Максимальное количество возвращаемых записей

        Returns:
            List[T]: Список сущностей
        """
        raise NotImplementedError

    @abstractmethod
    async def create(self, entity: T) -> T:
        """Создать новую сущность.

        Args:
            entity: Сущность для создания

        Returns:
            T: Созданная сущность
        """
        raise NotImplementedError

    @abstractmethod
    async def update(self, entity: T) -> T:
        """Обновить существующую сущность.

        Args:
            entity: Сущность с обновленными данными

        Returns:
            T: Обновленная сущность
        """
        raise NotImplementedError

    @abstractmethod
    async def delete(self, entity_id: UUID) -> bool:
        """Удалить сущность.

        Args:
            entity_id: Идентификатор сущности

        Returns:
            bool: True если успешно удалено, иначе False
        """
        raise NotImplementedError

    @abstractmethod
    async def count(self) -> int:
        """Get total number of entities.

        Returns:
            int: Number of entities
        """
        raise NotImplementedError

    @abstractmethod
    async def exists(self, entity_id: UUID) -> bool:
        """Check if entity exists by ID.

        Args:
            entity_id: Entity ID

        Returns:
            bool: True if entity exists
        """
        raise NotImplementedError
