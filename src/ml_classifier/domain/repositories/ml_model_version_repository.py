"""Repository interface for ML model versions."""
from abc import abstractmethod
from typing import List, Optional
from uuid import UUID

from ml_classifier.domain.entities.ml_model_version import (
    MLModelVersion,
    ModelVersionStatus,
)
from ml_classifier.domain.repositories.base import Repository


class MLModelVersionRepository(Repository[MLModelVersion]):
    """Repository interface for ML model versions."""

    @abstractmethod
    async def get_by_model_id(self, model_id: UUID) -> List[MLModelVersion]:
        """
        Get all versions of a model.

        Args:
            model_id: The ID of the model

        Returns:
            List[MLModelVersion]: All versions of the specified model
        """
        raise NotImplementedError

    @abstractmethod
    async def get_default_version(self, model_id: UUID) -> Optional[MLModelVersion]:
        """
        Get default version of a model.

        Args:
            model_id: The ID of the model

        Returns:
            Optional[MLModelVersion]: Default version or None
        """
        raise NotImplementedError

    @abstractmethod
    async def set_default_version(self, version_id: UUID) -> MLModelVersion:
        """
        Set a version as default for its model.

        Args:
            version_id: The ID of the version to set as default

        Returns:
            MLModelVersion: Updated version entity
        """
        raise NotImplementedError

    @abstractmethod
    async def unset_default_versions(self, model_id: UUID) -> None:
        """
        Unset default flag for all versions of a model.

        Args:
            model_id: The ID of the model
        """
        raise NotImplementedError

    @abstractmethod
    async def get_by_model_id_and_version(
        self, model_id: UUID, version: str
    ) -> Optional[MLModelVersion]:
        """
        Get specific version of a model.

        Args:
            model_id: The ID of the model
            version: Version string (semver)

        Returns:
            Optional[MLModelVersion]: Found version or None
        """
        raise NotImplementedError

    @abstractmethod
    async def update_status(
        self, version_id: UUID, status: ModelVersionStatus
    ) -> MLModelVersion:
        """
        Update version status.

        Args:
            version_id: The ID of the version
            status: New status

        Returns:
            MLModelVersion: Updated version entity
        """
        raise NotImplementedError
