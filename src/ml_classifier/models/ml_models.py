"""ML model-related data models."""
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Any
from uuid import UUID

from pydantic import BaseModel, Field, validator


class ModelType(str, Enum):
    """Available model types."""

    CLASSIFICATION = "classification"
    REGRESSION = "regression"
    CLUSTERING = "clustering"
    NLP = "nlp"
    COMPUTER_VISION = "computer_vision"


class ModelAlgorithm(str, Enum):
    """Available model algorithms."""

    SVM = "svm"
    RANDOM_FOREST = "random_forest"
    LOGISTIC_REGRESSION = "logistic_regression"
    NAIVE_BAYES = "naive_bayes"
    NEURAL_NETWORK = "neural_network"
    DECISION_TREE = "decision_tree"
    GRADIENT_BOOSTING = "gradient_boosting"
    KNN = "knn"
    LINEAR_REGRESSION = "linear_regression"
    K_MEANS = "k_means"


class ModelVersionStatus(str, Enum):
    """Available model version statuses."""

    TRAINED = "trained"
    TESTING = "testing"
    PRODUCTION = "production"


class ModelBase(BaseModel):
    """Base model for ML model data."""

    name: str
    description: Optional[str] = None
    model_type: ModelType
    algorithm: ModelAlgorithm
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    price_per_call: Decimal = Field(default=Decimal("0.0"), ge=0)


class ModelCreate(ModelBase):
    """Model for creating a new ML model."""

    is_active: bool = True


class ModelUpdate(BaseModel):
    """Model for updating an existing ML model."""

    name: Optional[str] = None
    description: Optional[str] = None
    model_type: Optional[ModelType] = None
    algorithm: Optional[ModelAlgorithm] = None
    input_schema: Optional[Dict[str, Any]] = None
    output_schema: Optional[Dict[str, Any]] = None
    price_per_call: Optional[Decimal] = None
    is_active: Optional[bool] = None


class ModelResponse(ModelBase):
    """Response model for ML model data."""

    id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ModelListResponse(BaseModel):
    """Response model for listing ML models."""

    items: List[ModelResponse]
    total: int
    page: int
    size: int


class ModelVersionCreate(BaseModel):
    """Model for creating a new ML model version."""

    version: str  # Semantic versioning
    metrics: Dict[str, Any] = Field(default_factory=dict)
    parameters: Dict[str, Any] = Field(default_factory=dict)
    status: ModelVersionStatus = ModelVersionStatus.TRAINED

    @validator("version")
    def validate_semver(cls, v):
        """Validate semantic versioning format."""
        import re

        pattern = (
            r"^(0|[1-9]\d*)\."  # Major version
            r"(0|[1-9]\d*)\."  # Minor version
            r"(0|[1-9]\d*)"  # Patch version
            r"(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)"
            r"(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?"  # Pre-release
            r"(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"  # Build metadata
        )
        if not re.match(pattern, v):
            raise ValueError("Version must follow semantic versioning (e.g., 1.0.0)")
        return v


class ModelVersionResponse(BaseModel):
    """Response model for ML model version data."""

    id: UUID
    model_id: UUID
    version: str
    file_path: str
    metrics: Dict[str, Any]
    parameters: Dict[str, Any]
    is_default: bool
    created_by: UUID
    file_size: int
    status: ModelVersionStatus
    created_at: datetime
    updated_at: datetime


class ModelVersionListResponse(BaseModel):
    """Response model for listing ML model versions."""

    items: List[ModelVersionResponse]
    total: int
