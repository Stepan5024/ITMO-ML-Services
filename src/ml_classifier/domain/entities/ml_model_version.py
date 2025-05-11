"""ML Model Version domain entity."""
from enum import Enum
from typing import Dict, Any
from uuid import UUID

from ml_classifier.domain.entities.base import Entity


class ModelVersionStatus(str, Enum):
    """Status of a model version."""

    TRAINED = "trained"
    TESTING = "testing"
    PRODUCTION = "production"


class MLModelVersion(Entity):
    """Version of a machine learning model."""

    model_id: UUID
    version: str
    file_path: str
    metrics: Dict[str, Any]
    parameters: Dict[str, Any]
    is_default: bool = False
    created_by: UUID
    file_size: int
    status: ModelVersionStatus = ModelVersionStatus.TRAINED

    def __str__(self) -> str:
        """String representation of the model version."""
        return f"MLModelVersion({self.version}, model_id={self.model_id}, status={self.status})"
