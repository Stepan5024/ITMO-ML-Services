"""Use cases for ML model and version management."""
import os
import re
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Tuple, Any
from uuid import UUID

from fastapi import UploadFile
import joblib

from ml_classifier.domain.entities.ml_model import MLModel, ModelType, ModelAlgorithm
from ml_classifier.domain.entities.ml_model_version import (
    MLModelVersion,
    ModelVersionStatus,
)
from ml_classifier.domain.repositories.ml_model_repository import MLModelRepository
from ml_classifier.domain.repositories.ml_model_version_repository import (
    MLModelVersionRepository,
)


class ModelUseCase:
    """Use case for ML model management."""

    def __init__(
        self,
        model_repository: MLModelRepository,
        version_repository: MLModelVersionRepository,
        model_storage_path: str = "models",
    ):
        """
        Initialize use case with repositories.

        Args:
            model_repository: Repository for ML models
            version_repository: Repository for ML model versions
            model_storage_path: Path for storing model files
        """
        self.model_repository = model_repository
        self.version_repository = version_repository
        self.model_storage_path = model_storage_path

        os.makedirs(self.model_storage_path, exist_ok=True)

    async def create_model(
        self, model_data: Dict[str, Any]
    ) -> Tuple[bool, str, Optional[MLModel]]:
        """
        Create a new ML model.

        Args:
            model_data: Model metadata

        Returns:
            Tuple[bool, str, Optional[MLModel]]: (success, message, created_model)
        """
        existing_model = await self.model_repository.get_by_name(model_data["name"])
        if existing_model:
            return False, f"Model with name '{model_data['name']}' already exists", None

        required_fields = [
            "name",
            "model_type",
            "algorithm",
            "input_schema",
            "output_schema",
        ]
        for field in required_fields:
            if field not in model_data:
                return False, f"Missing required field: {field}", None

        try:
            model_type = ModelType(model_data["model_type"])
            algorithm = ModelAlgorithm(model_data["algorithm"])
        except ValueError as e:
            return False, f"Invalid enum value: {str(e)}", None

        model = MLModel(
            id=uuid.uuid4(),
            name=model_data["name"],
            description=model_data.get("description"),
            model_type=model_type,
            algorithm=algorithm,
            input_schema=model_data["input_schema"],
            output_schema=model_data["output_schema"],
            is_active=model_data.get("is_active", True),
            price_per_call=Decimal(str(model_data.get("price_per_call", 0.0))),
        )

        try:
            created_model = await self.model_repository.create(model)
            return True, "Model created successfully", created_model
        except Exception as e:
            return False, f"Error creating model: {str(e)}", None

    async def update_model(
        self, model_id: UUID, model_data: Dict[str, Any]
    ) -> Tuple[bool, str, Optional[MLModel]]:
        """
        Update ML model metadata.

        Args:
            model_id: Model ID
            model_data: Updated model data

        Returns:
            Tuple[bool, str, Optional[MLModel]]: (success, message, updated_model)
        """
        model = await self.model_repository.get_by_id(model_id)
        if not model:
            return False, f"Model with ID {model_id} not found", None

        if "name" in model_data and model_data["name"] != model.name:
            existing = await self.model_repository.get_by_name(model_data["name"])
            if existing and existing.id != model_id:
                return (
                    False,
                    f"Model with name '{model_data['name']}' already exists",
                    None,
                )

        model_type = model.model_type
        algorithm = model.algorithm

        if "model_type" in model_data:
            try:
                model_type = ModelType(model_data["model_type"])
            except ValueError as e:
                return False, f"Invalid model type: {str(e)}", None

        if "algorithm" in model_data:
            try:
                algorithm = ModelAlgorithm(model_data["algorithm"])
            except ValueError as e:
                return False, f"Invalid algorithm: {str(e)}", None

        updated_model = MLModel(
            id=model.id,
            name=model_data.get("name", model.name),
            description=model_data.get("description", model.description),
            model_type=model_type,
            algorithm=algorithm,
            input_schema=model_data.get("input_schema", model.input_schema),
            output_schema=model_data.get("output_schema", model.output_schema),
            is_active=model_data.get("is_active", model.is_active),
            price_per_call=Decimal(
                str(model_data.get("price_per_call", model.price_per_call))
            ),
            created_at=model.created_at,
            updated_at=datetime.utcnow(),
        )

        try:
            updated = await self.model_repository.update(updated_model)
            return True, "Model updated successfully", updated
        except Exception as e:
            return False, f"Error updating model: {str(e)}", None

    async def delete_model(self, model_id: UUID) -> Tuple[bool, str]:
        """
        Delete an ML model and all its versions.

        Args:
            model_id: Model ID

        Returns:
            Tuple[bool, str]: (success, message)
        """
        model = await self.model_repository.get_by_id(model_id)
        if not model:
            return False, f"Model with ID {model_id} not found"

        versions = await self.version_repository.get_by_model_id(model_id)

        for version in versions:
            try:
                if os.path.exists(version.file_path):
                    os.remove(version.file_path)
                await self.version_repository.delete(version.id)
            except Exception as e:
                return False, f"Error deleting version {version.id}: {str(e)}"

        try:
            success = await self.model_repository.delete(model_id)
            if success:
                return True, "Model and all its versions deleted successfully"
            else:
                return False, "Failed to delete model"
        except Exception as e:
            return False, f"Error deleting model: {str(e)}"

    async def get_model_by_id(self, model_id: UUID) -> Optional[MLModel]:
        """
        Get ML model by ID.

        Args:
            model_id: Model ID

        Returns:
            Optional[MLModel]: Found model or None
        """
        return await self.model_repository.get_by_id(model_id)

    async def list_models(
        self,
        skip: int = 0,
        limit: int = 20,
        search: Optional[str] = None,
        model_type: Optional[ModelType] = None,
        is_active: Optional[bool] = None,
    ) -> Tuple[List[MLModel], int]:
        """
        Get list of models with filters.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            search: Search term for name or description
            model_type: Filter by model type
            is_active: Filter by active status

        Returns:
            Tuple[List[MLModel], int]: Models and total count
        """
        if search:
            models = await self.model_repository.search_models(
                query=search, model_type=model_type, skip=skip, limit=limit
            )
            total = len(models) + skip
        else:
            models = await self.model_repository.list(skip=skip, limit=limit)
            total = await self.model_repository.count()

        if is_active is not None:
            models = [model for model in models if model.is_active == is_active]

        return models, total

    async def activate_model(
        self, model_id: UUID
    ) -> Tuple[bool, str, Optional[MLModel]]:
        """
        Activate an ML model.

        Args:
            model_id: Model ID

        Returns:
            Tuple[bool, str, Optional[MLModel]]: (success, message, updated_model)
        """
        try:
            model = await self.model_repository.get_by_id(model_id)
            if not model:
                return False, f"Model with ID {model_id} not found", None

            if model.is_active:
                return True, "Model is already active", model

            updated = await self.model_repository.update_status(model_id, True)
            return True, "Model activated successfully", updated
        except Exception as e:
            return False, f"Error activating model: {str(e)}", None

    async def deactivate_model(
        self, model_id: UUID
    ) -> Tuple[bool, str, Optional[MLModel]]:
        """
        Deactivate an ML model.

        Args:
            model_id: Model ID

        Returns:
            Tuple[bool, str, Optional[MLModel]]: (success, message, updated_model)
        """
        try:
            model = await self.model_repository.get_by_id(model_id)
            if not model:
                return False, f"Model with ID {model_id} not found", None

            if not model.is_active:
                return True, "Model is already inactive", model

            updated = await self.model_repository.update_status(model_id, False)
            return True, "Model deactivated successfully", updated
        except Exception as e:
            return False, f"Error deactivating model: {str(e)}", None


class ModelVersionUseCase:
    """Use case for ML model version management."""

    def __init__(
        self,
        model_repository: MLModelRepository,
        version_repository: MLModelVersionRepository,
        model_storage_path: str = "models",
    ):
        """
        Initialize use case with repositories.

        Args:
            model_repository: Repository for ML models
            version_repository: Repository for ML model versions
            model_storage_path: Path for storing model files
        """
        self.model_repository = model_repository
        self.version_repository = version_repository
        self.model_storage_path = model_storage_path

        os.makedirs(self.model_storage_path, exist_ok=True)

    async def create_version(
        self,
        model_id: UUID,
        version_data: Dict[str, Any],
        model_file: UploadFile,
        vectorizer_file: Optional[UploadFile] = None,
        user_id: UUID = None,
    ) -> Tuple[bool, str, Optional[MLModelVersion]]:
        """
        Create a new model version with model file and optional vectorizer.
        """
        model = await self.model_repository.get_by_id(model_id)
        if not model:
            return False, f"Model with ID {model_id} not found", None

        version = version_data.get("version")
        if not version or not self._is_valid_semver(version):
            return (
                False,
                "Invalid version format. Use semantic versioning (e.g. 1.0.0)",
                None,
            )

        existing = await self.version_repository.get_by_model_id_and_version(
            model_id, version
        )
        if existing:
            return False, f"Version {version} already exists", None

        model_dir = os.path.join(self.model_storage_path, str(model_id))
        os.makedirs(model_dir, exist_ok=True)

        version_id = uuid.uuid4()
        version_dir = os.path.join(model_dir, str(version_id))
        os.makedirs(version_dir, exist_ok=True)

        model_file_path = os.path.join(version_dir, "model.joblib")
        vectorizer_file_path = None

        try:
            model_contents = await model_file.read()
            model_file_size = len(model_contents)

            with open(model_file_path, "wb") as f:
                f.write(model_contents)

            try:
                joblib.load(model_file_path)
            except Exception as e:
                if os.path.exists(model_file_path):
                    os.remove(model_file_path)
                return False, f"Invalid model file: {str(e)}", None
            if vectorizer_file:
                vectorizer_file_path = os.path.join(version_dir, "vectorizer.pkl")
                vectorizer_contents = await vectorizer_file.read()

                with open(vectorizer_file_path, "wb") as f:
                    f.write(vectorizer_contents)

                try:
                    joblib.load(vectorizer_file_path)
                except Exception as e:
                    if os.path.exists(vectorizer_file_path):
                        os.remove(vectorizer_file_path)
                    if os.path.exists(model_file_path):
                        os.remove(model_file_path)
                    return False, f"Invalid vectorizer file: {str(e)}", None
            is_default = await self._check_is_default(model_id)

            version_entity = MLModelVersion(
                id=version_id,
                model_id=model_id,
                version=version,
                file_path=model_file_path,
                metrics=version_data.get("metrics", {}),
                parameters=version_data.get("parameters", {}),
                is_default=is_default,
                created_by=user_id,
                file_size=model_file_size,
                status=ModelVersionStatus(version_data.get("status", "trained")),
            )
            parameters = version_data.get("parameters", {}).copy()
            if vectorizer_file_path:
                parameters["vectorizer_path"] = vectorizer_file_path

            version_entity = MLModelVersion(
                id=version_id,
                model_id=model_id,
                version=version,
                file_path=model_file_path,
                metrics=version_data.get("metrics", {}),
                parameters=parameters,
                is_default=is_default,
                created_by=user_id,
                file_size=model_file_size,
                status=ModelVersionStatus(version_data.get("status", "trained")),
            )

            created = await self.version_repository.create(version_entity)
            return True, "Model version created successfully", created

        except Exception as e:
            if os.path.exists(model_file_path):
                os.remove(model_file_path)
            if vectorizer_file_path and os.path.exists(vectorizer_file_path):
                os.remove(vectorizer_file_path)
            return False, f"Error creating model version: {str(e)}", None

    async def _check_is_default(self, model_id: UUID) -> bool:
        """Check if this should be default version"""
        versions = await self.version_repository.get_by_model_id(model_id)
        return len(versions) == 0

    async def get_version(self, version_id: UUID) -> Optional[MLModelVersion]:
        """
        Get model version by ID.

        Args:
            version_id: Version ID

        Returns:
            Optional[MLModelVersion]: Found version or None
        """
        return await self.version_repository.get_by_id(version_id)

    async def list_versions(self, model_id: UUID) -> List[MLModelVersion]:
        """
        Get all versions of a model.

        Args:
            model_id: Model ID

        Returns:
            List[MLModelVersion]: All versions of the model
        """
        return await self.version_repository.get_by_model_id(model_id)

    async def set_default_version(
        self, version_id: UUID
    ) -> Tuple[bool, str, Optional[MLModelVersion]]:
        """
        Set a version as the default for its model.

        Args:
            version_id: Version ID

        Returns:
            Tuple[bool, str, Optional[MLModelVersion]]: (success, message, updated_version)
        """
        version = await self.version_repository.get_by_id(version_id)
        if not version:
            return False, f"Version with ID {version_id} not found", None

        try:
            await self.version_repository.unset_default_versions(version.model_id)

            updated = await self.version_repository.set_default_version(version_id)
            return True, "Default version set successfully", updated
        except Exception as e:
            return False, f"Error setting default version: {str(e)}", None

    async def delete_version(self, version_id: UUID) -> Tuple[bool, str]:
        """
        Delete a model version.

        Args:
            version_id: Version ID

        Returns:
            Tuple[bool, str]: (success, message)
        """
        version = await self.version_repository.get_by_id(version_id)
        if not version:
            return False, f"Version with ID {version_id} not found"

        if version.is_default:
            versions = await self.version_repository.get_by_model_id(version.model_id)
            if len(versions) > 1:
                return (
                    False,
                    "Cannot delete default version. Set another version as default first.",
                )

        try:
            if os.path.exists(version.file_path):
                os.remove(version.file_path)

            success = await self.version_repository.delete(version_id)
            if success:
                return True, "Version deleted successfully"
            else:
                return False, "Failed to delete version"
        except Exception as e:
            return False, f"Error deleting version: {str(e)}"

    async def get_default_version(self, model_id: UUID) -> Optional[MLModelVersion]:
        """
        Get the default version of a model.

        Args:
            model_id: Model ID

        Returns:
            Optional[MLModelVersion]: Default version or None
        """
        return await self.version_repository.get_default_version(model_id)

    async def compare_versions(
        self, version_id1: UUID, version_id2: UUID
    ) -> Tuple[bool, str, Optional[Dict]]:
        """
        Compare metrics of two model versions.

        Args:
            version_id1: First version ID
            version_id2: Second version ID

        Returns:
            Tuple[bool, str, Optional[Dict]]: (success, message, comparison_result)
        """
        version1 = await self.version_repository.get_by_id(version_id1)
        if not version1:
            return False, f"Version with ID {version_id1} not found", None

        version2 = await self.version_repository.get_by_id(version_id2)
        if not version2:
            return False, f"Version with ID {version_id2} not found", None

        if version1.model_id != version2.model_id:
            return False, "Cannot compare versions from different models", None

        try:
            metrics1 = version1.metrics
            metrics2 = version2.metrics

            common_metrics = set(metrics1.keys()) & set(metrics2.keys())

            result = {
                "version1": {
                    "id": str(version1.id),
                    "version": version1.version,
                    "metrics": metrics1,
                },
                "version2": {
                    "id": str(version2.id),
                    "version": version2.version,
                    "metrics": metrics2,
                },
                "comparison": {},
            }

            for metric in common_metrics:
                if isinstance(metrics1[metric], (int, float)) and isinstance(
                    metrics2[metric], (int, float)
                ):
                    diff = metrics2[metric] - metrics1[metric]
                    result["comparison"][metric] = {
                        "diff": diff,
                        "diff_percent": (diff / metrics1[metric]) * 100
                        if metrics1[metric] != 0
                        else float("inf"),
                        "improved": diff > 0
                        if metric.startswith(("accuracy", "f1", "precision", "recall"))
                        else diff < 0,
                    }

            return True, "Version comparison successful", result
        except Exception as e:
            return False, f"Error comparing versions: {str(e)}", None

    def _is_valid_semver(self, version: str) -> bool:
        """
        Validate semantic versioning format.

        Args:
            version: Version string to validate

        Returns:
            bool: True if valid semantic version
        """
        pattern = (
            r"^(0|[1-9]\d*)\."  # Major version
            r"(0|[1-9]\d*)\."  # Minor version
            r"(0|[1-9]\d*)"  # Patch version
            r"(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)"
            r"(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?"  # Pre-release
            r"(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"  # Build metadata
        )
        return bool(re.match(pattern, version))


def get_model_use_case(
    model_repository: MLModelRepository,
    version_repository: MLModelVersionRepository,
) -> ModelUseCase:
    """Get Model UseCase instance."""
    return ModelUseCase(model_repository, version_repository)


def get_model_version_use_case(
    model_repository: MLModelRepository,
    version_repository: MLModelVersionRepository,
) -> ModelVersionUseCase:
    """Get ModelVersion UseCase instance."""
    return ModelVersionUseCase(model_repository, version_repository)
