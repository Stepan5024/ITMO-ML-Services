"""Model loading functionality for ML operations."""
import pickle
from functools import lru_cache
from typing import Any, Dict, Optional, Tuple
import os

from uuid import UUID
import joblib
from loguru import logger
from pydantic import BaseModel

from ml_classifier.domain.repositories.ml_model_repository import MLModelRepository
from ml_classifier.domain.repositories.ml_model_version_repository import (
    MLModelVersionRepository,
)


class ModelMetadata(BaseModel):
    """Metadata about a model version."""

    model_id: UUID
    version_id: UUID
    model_name: str
    version: str
    algorithm: str
    input_schema: Dict
    output_schema: Dict
    metrics: Dict
    parameters: Dict
    file_path: str
    created_at: str
    is_default: bool


class ModelNotFoundError(Exception):
    """Raised when a model is not found."""

    pass


class ModelVersionNotFoundError(Exception):
    """Raised when a model version is not found."""

    pass


class ModelLoadError(Exception):
    """Raised when there's an error loading a model."""

    pass


class ModelValidator:
    """Validates loaded models."""

    def validate(self, model: Any) -> Tuple[bool, str]:
        """
        Validate if the loaded object is a valid ML model.

        Args:
            model: The loaded model to validate

        Returns:
            Tuple[bool, str]: (is_valid, error_message)
        """
        if model is None:
            return False, "Model is None"

        if not hasattr(model, "predict"):
            return False, "Model doesn't have a predict method"

        return True, ""


class ModelLoader:
    """Service for loading ML models from storage."""

    def __init__(
        self,
        model_repository: MLModelRepository,
        model_version_repository: MLModelVersionRepository,
        model_storage_path: str = "models",
        validator: Optional[ModelValidator] = None,
        cache_size: int = 10,
    ):
        """
        Initialize the model loader.

        Args:
            model_repository: Repository for ML models
            model_version_repository: Repository for ML model versions
            model_storage_path: Path to the model storage directory
            validator: Optional model validator
            cache_size: Size of the LRU cache for models
        """
        self.model_repository = model_repository
        self.model_version_repository = model_version_repository
        self.model_storage_path = model_storage_path
        self.validator = validator or ModelValidator()
        self.cache_size = cache_size

        os.makedirs(model_storage_path, exist_ok=True)

    async def load_vectorizer(self, model_id: UUID, version_id: Optional[UUID] = None):
        """
        Load a vectorizer (e.g. TF-IDF) for the given model and version.
        """
        try:
            version = await self.model_version_repository.get_latest_or_id(
                model_id, version_id
            )

            if version.parameters and "vectorizer_path" in version.parameters:
                vec_path = version.parameters["vectorizer_path"]
                logger.info(
                    f"Loading vectorizer from path stored in parameters: {vec_path}"
                )
                if os.path.exists(vec_path):
                    return joblib.load(vec_path)

            version_dir = os.path.dirname(version.file_path)
            standard_vec_path = os.path.join(version_dir, "vectorizer.pkl")
            logger.info(f"Trying standard vectorizer location: {standard_vec_path}")

            if os.path.exists(standard_vec_path):
                return joblib.load(standard_vec_path)

            base_dir = os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )
            common_vec_path = os.path.join(base_dir, "models", "tfidf_vectorizer.pkl")

            if os.path.exists(common_vec_path):
                logger.info(f"Using common vectorizer from: {common_vec_path}")
                return joblib.load(common_vec_path)

            logger.warning(
                f"Vectorizer not found for model {model_id}. Tried paths: {standard_vec_path} and {common_vec_path}"
            )
            raise ModelNotFoundError(f"Vectorizer not found for model {model_id}")

        except Exception as e:
            logger.exception(f"Error loading vectorizer for model {model_id}: {str(e)}")
            raise ModelNotFoundError(
                f"Error loading vectorizer for model {model_id}: {str(e)}"
            )

    @lru_cache(maxsize=10)
    async def load_model(
        self, model_id: UUID, version_id: Optional[UUID] = None
    ) -> Any:
        """
        Load a model by its ID and optionally a specific version ID.

        Args:
            model_id: The ID of the model to load
            version_id: Optional ID of the specific version to load

        Returns:
            The loaded model object

        Raises:
            ModelNotFoundError: If the model is not found
            ModelVersionNotFoundError: If the version is not found
            ModelLoadError: If there's an error loading the model
        """
        logger.info(f"Loading model {model_id} (version: {version_id or 'default'})")

        model_entity = await self.model_repository.get_by_id(model_id)
        if not model_entity:
            logger.error(f"Model not found: {model_id}")
            raise ModelNotFoundError(f"Model with ID {model_id} not found")

        if version_id:
            version_entity = await self.model_version_repository.get_by_id(version_id)
            if not version_entity or version_entity.model_id != model_id:
                logger.error(f"Version {version_id} not found for model {model_id}")
                raise ModelVersionNotFoundError(
                    f"Version {version_id} for model {model_id} not found"
                )
        else:
            version_entity = await self.model_version_repository.get_default_version(
                model_id
            )
            if not version_entity:
                logger.error(f"No default version found for model {model_id}")
                raise ModelVersionNotFoundError(
                    f"No default version found for model {model_id}"
                )

        try:
            file_path = version_entity.file_path
            logger.info(f"Loading model from {file_path}")

            if file_path.endswith(".pkl"):
                with open(file_path, "rb") as f:
                    model = pickle.load(f)
            elif file_path.endswith(".joblib"):
                model = joblib.load(file_path)
            else:
                raise ModelLoadError(f"Unsupported model file format: {file_path}")

            is_valid, error_msg = self.validator.validate(model)
            if not is_valid:
                raise ModelLoadError(f"Invalid model: {error_msg}")

            logger.info(
                f"Model {model_id} (version: {version_entity.version}) loaded successfully"
            )
            return model

        except Exception as e:
            logger.exception(f"Error loading model {model_id}: {str(e)}")
            raise ModelLoadError(f"Error loading model {model_id}: {str(e)}")

    async def load_model_by_name(
        self, model_name: str, version: Optional[str] = None
    ) -> Any:
        """
        Load a model by its name and optionally a specific version.

        Args:
            model_name: The name of the model to load
            version: Optional version string of the model

        Returns:
            The loaded model object

        Raises:
            ModelNotFoundError: If the model is not found
            ModelVersionNotFoundError: If the version is not found
            ModelLoadError: If there's an error loading the model
        """
        logger.info(
            f"Loading model by name: {model_name} (version: {version or 'default'})"
        )

        model_entity = await self.model_repository.get_by_name(model_name)
        if not model_entity:
            logger.error(f"Model not found: {model_name}")
            raise ModelNotFoundError(f"Model with name {model_name} not found")

        if version:
            version_entity = (
                await self.model_version_repository.get_by_model_id_and_version(
                    model_entity.id, version
                )
            )
            if not version_entity:
                logger.error(f"Version {version} not found for model {model_name}")
                raise ModelVersionNotFoundError(
                    f"Version {version} for model {model_name} not found"
                )
            return await self.load_model(model_entity.id, version_entity.id)
        else:
            return await self.load_model(model_entity.id)

    async def get_model_metadata(
        self, model_id: UUID, version_id: Optional[UUID] = None
    ) -> ModelMetadata:
        """
        Get metadata for a model and optionally a specific version.

        Args:
            model_id: The ID of the model
            version_id: Optional ID of the specific version

        Returns:
            ModelMetadata object

        Raises:
            ModelNotFoundError: If the model is not found
            ModelVersionNotFoundError: If the version is not found
        """
        logger.info(
            f"Getting metadata for model {model_id} (version: {version_id or 'default'})"
        )

        model_entity = await self.model_repository.get_by_id(model_id)
        if not model_entity:
            logger.error(f"Model not found: {model_id}")
            raise ModelNotFoundError(f"Model with ID {model_id} not found")

        if version_id:
            version_entity = await self.model_version_repository.get_by_id(version_id)
            if not version_entity or version_entity.model_id != model_id:
                logger.error(f"Version {version_id} not found for model {model_id}")
                raise ModelVersionNotFoundError(
                    f"Version {version_id} for model {model_id} not found"
                )
        else:
            version_entity = await self.model_version_repository.get_default_version(
                model_id
            )
            if not version_entity:
                logger.error(f"No default version found for model {model_id}")
                raise ModelVersionNotFoundError(
                    f"No default version found for model {model_id}"
                )

        return ModelMetadata(
            model_id=model_entity.id,
            version_id=version_entity.id,
            model_name=model_entity.name,
            version=version_entity.version,
            algorithm=model_entity.algorithm,
            input_schema=model_entity.input_schema,
            output_schema=model_entity.output_schema,
            metrics=version_entity.metrics,
            parameters=version_entity.parameters,
            file_path=version_entity.file_path,
            created_at=version_entity.created_at.isoformat(),
            is_default=version_entity.is_default,
        )
