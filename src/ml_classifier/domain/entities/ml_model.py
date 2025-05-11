"""ML Model domain entity."""
from decimal import Decimal
from enum import Enum
from typing import Dict, Any, Optional

from pydantic import Field

from ml_classifier.domain.entities.base import Entity


class ModelType(str, Enum):
    """Type of machine learning model."""

    CLASSIFICATION = "classification"
    REGRESSION = "regression"
    CLUSTERING = "clustering"
    NLP = "nlp"
    COMPUTER_VISION = "computer_vision"


class ModelAlgorithm(str, Enum):
    """Algorithm used in the machine learning model."""

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


class MLModel(Entity):
    """Machine Learning model entity."""

    name: str
    description: Optional[str] = None
    model_type: ModelType
    algorithm: ModelAlgorithm
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    is_active: bool = True
    price_per_call: Decimal = Field(default=Decimal("0.0"), ge=0)

    def __str__(self) -> str:
        """String representation of the model."""
        return (
            f"MLModel({self.name}, type={self.model_type}, algorithm={self.algorithm})"
        )
