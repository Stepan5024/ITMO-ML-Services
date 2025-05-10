"""Use case for model version management."""
from typing import Dict, Optional, Tuple, Any
from uuid import UUID

from ml_classifier.domain.entities.ml_model_version import (
    MLModelVersion,
    ModelVersionStatus,
)
from ml_classifier.domain.repositories.ml_model_version_repository import (
    MLModelVersionRepository,
)
from ml_classifier.infrastructure.ml.model_storage import ModelStorage


class ModelVersionUseCase:
    """Use case for managing model versions."""

    def __init__(
        self, version_repository: MLModelVersionRepository, model_storage: ModelStorage
    ):
        """Initialize with repositories and storage."""
        self.version_repository = version_repository
        self.model_storage = model_storage

    async def create_version(
        self,
        model_id: UUID,
        version_data: Dict[str, Any],
        file_content: bytes,
        user_id: UUID,
    ) -> Tuple[bool, str, Optional[MLModelVersion]]:
        """
        Create a new model version with file.

        Args:
            model_id: Parent model ID
            version_data: Version metadata
            file_content: Model file binary content
            user_id: ID of the user creating the version

        Returns:
            Tuple[bool, str, Optional[MLModelVersion]]: (success, message, created_version)
        """
        # Check if version already exists for this model
        existing = await self.version_repository.get_by_model_id_and_version(
            model_id, version_data["version"]
        )
        if existing:
            return (
                False,
                f"Version {version_data['version']} already exists for this model",
                None,
            )

        # Save model file
        success, message, file_path = self.model_storage.save_model(
            file_content, model_id, version_data["version"]
        )
        if not success:
            return False, message, None

        # Get file size
        file_size = self.model_storage.get_model_size(file_path)

        # Check if this is the first version (should be default)
        versions = await self.version_repository.get_by_model_id(model_id)
        is_default = len(versions) == 0

        # Create version entity
        version_entity = MLModelVersion(
            model_id=model_id,
            version=version_data["version"],
            file_path=file_path,
            metrics=version_data.get("metrics", {}),
            parameters=version_data.get("parameters", {}),
            is_default=is_default,
            created_by=user_id,
            file_size=file_size,
            status=version_data.get("status", ModelVersionStatus.TRAINED),
        )

        try:
            # Save to repository
            created = await self.version_repository.create(version_entity)
            return True, "Model version created successfully", created
        except Exception as e:
            # Cleanup file on failure
            self.model_storage.delete_model(file_path)
            return False, f"Error creating version: {str(e)}", None
