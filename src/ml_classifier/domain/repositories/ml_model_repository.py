"""Repository interface for ML models."""
from abc import abstractmethod
from typing import List, Optional
from uuid import UUID

from ml_classifier.domain.entities.ml_model import MLModel, ModelType
from ml_classifier.domain.repositories.base import Repository


class MLModelRepository(Repository[MLModel]):
    """Repository interface for ML models."""

    @abstractmethod
    async def get_by_name(self, name: str) -> Optional[MLModel]:
        """
        Get model by name.

        Args:
            name: The name of the model to find

        Returns:
            Optional[MLModel]: Found model or None
        """
        raise NotImplementedError

    @abstractmethod
    async def get_active_models(self) -> List[MLModel]:
        """
        Get all active models.

        Returns:
            List[MLModel]: List of active models
        """
        raise NotImplementedError

    @abstractmethod
    async def search_models(
        self,
        query: str,
        model_type: Optional[ModelType] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> List[MLModel]:
        """
        Search models by name, description, or algorithm.

        Args:
            query: Search term
            model_type: Optional filter by model type
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List[MLModel]: List of matching models
        """
        raise NotImplementedError

    @abstractmethod
    async def update_status(self, model_id: UUID, is_active: bool) -> MLModel:
        """
        Update model status (active/inactive).

        Args:
            model_id: The ID of the model to update
            is_active: New active status

        Returns:
            MLModel: Updated model
        """
        raise NotImplementedError

    @abstractmethod
    async def get_model_types(self) -> List[ModelType]:
        """
        Get all unique model types.

        Returns:
            List[ModelType]: List of model types
        """
        raise NotImplementedError
