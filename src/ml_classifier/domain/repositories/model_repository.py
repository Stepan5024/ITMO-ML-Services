"""Репозиторий для работы с ML моделями."""
from abc import abstractmethod
from typing import List, Optional

from ml_classifier.domain.entities import Model
from ml_classifier.domain.repositories.base import Repository


class ModelRepository(Repository[Model]):
    """Интерфейс репозитория для работы с ML моделями."""

    @abstractmethod
    async def get_active_models(self) -> List[Model]:
        """Получить все активные модели.

        Returns:
            List[Model]: Список активных моделей
        """
        raise NotImplementedError

    @abstractmethod
    async def get_by_name(self, name: str) -> Optional[Model]:
        """Получить модель по имени.

        Args:
            name: Имя модели

        Returns:
            Optional[Model]: Найденная модель или None
        """
        raise NotImplementedError

    @abstractmethod
    async def get_all_active(self) -> List[Model]:
        """Get all active models.

        Returns:
            List[Model]: List of active models
        """
        raise NotImplementedError

    @abstractmethod
    async def search_models(
        self, query: str, skip: int = 0, limit: int = 20
    ) -> List[Model]:
        """Search models by name or description.

        Args:
            query: Search query
            skip: Number of records to skip (for pagination)
            limit: Maximum number of records to return

        Returns:
            List[Model]: List of found models
        """
        raise NotImplementedError

    @abstractmethod
    async def get_latest_version(self, model_name: str) -> Optional[Model]:
        """Get latest version of a model by name.

        Args:
            model_name: Model name

        Returns:
            Optional[Model]: Latest version of the model or None
        """
        raise NotImplementedError
