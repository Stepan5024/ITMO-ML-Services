"""Scikit-learn model wrapper for ML operations."""
import os
import pickle
from typing import Any, Optional

import joblib
import numpy as np
from loguru import logger
from sklearn.base import BaseEstimator

from ml_classifier.infrastructure.ml.text_preprocessing import TextPreprocessor


class ScikitLearnModel:
    """Wrapper for scikit-learn models to provide unified interface."""

    def __init__(
        self,
        model: BaseEstimator,
        preprocessor: Optional[TextPreprocessor] = None,
        model_type: str = "classification",
    ):
        """
        Initialize scikit-learn model wrapper.

        Args:
            model: Scikit-learn model
            preprocessor: Text preprocessor for text input
            model_type: Type of model ('classification' or 'regression')
        """
        self.model = model
        self.preprocessor = preprocessor
        self.model_type = model_type

    def fit(self, X: Any, y: Any) -> "ScikitLearnModel":
        """
        Fit the model on training data.

        Args:
            X: Training data features
            y: Target values

        Returns:
            Self for chaining
        """
        # Preprocess text data if needed
        if self.preprocessor and isinstance(X, (list, str)):
            if isinstance(X, str):
                X = [X]
            X_processed = self.preprocessor.process(X)
        else:
            X_processed = X

        # Fit the model
        self.model.fit(X_processed, y)
        return self

    def predict(self, X: Any) -> np.ndarray:
        """
        Make predictions using the model.

        Args:
            X: Input features for prediction

        Returns:
            Model predictions
        """
        # Preprocess text data if needed
        if self.preprocessor and isinstance(X, (list, str)):
            if isinstance(X, str):
                X = [X]
            X_processed = self.preprocessor.process(X)
        else:
            X_processed = X

        # Make predictions
        return self.model.predict(X_processed)

    def predict_proba(self, X: Any) -> np.ndarray:
        """
        Make probability predictions (for classification models).

        Args:
            X: Input features for prediction

        Returns:
            Probability predictions

        Raises:
            AttributeError: If model doesn't support predict_proba
        """
        if not hasattr(self.model, "predict_proba"):
            raise AttributeError("This model doesn't support probability predictions")

        # Preprocess text data if needed
        if self.preprocessor and isinstance(X, (list, str)):
            if isinstance(X, str):
                X = [X]
            X_processed = self.preprocessor.process(X)
        else:
            X_processed = X

        # Make probability predictions
        return self.model.predict_proba(X_processed)

    def save(self, path: str, include_preprocessor: bool = True) -> str:
        """
        Save model to file.

        Args:
            path: Path to save the model
            include_preprocessor: Whether to save preprocessor with model

        Returns:
            Path where model was saved
        """
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(path), exist_ok=True)

        # Create save data
        save_data = {
            "model": self.model,
            "model_type": self.model_type,
            "preprocessor": self.preprocessor if include_preprocessor else None,
        }

        # Save model
        if path.endswith(".pkl"):
            with open(path, "wb") as f:
                pickle.dump(save_data, f)
        elif path.endswith(".joblib"):
            joblib.dump(save_data, path)
        else:
            path = f"{path}.joblib"
            joblib.dump(save_data, path)

        logger.info(f"Model saved to {path}")
        return path

    @classmethod
    def load(cls, path: str) -> "ScikitLearnModel":
        """
        Load model from file.

        Args:
            path: Path to the saved model

        Returns:
            Loaded model

        Raises:
            FileNotFoundError: If model file doesn't exist
            ValueError: If file format is not supported
        """
        if not os.path.exists(path):
            raise FileNotFoundError(f"Model file not found: {path}")

        # Load model data
        if path.endswith(".pkl"):
            with open(path, "rb") as f:
                save_data = pickle.load(f)
        elif path.endswith(".joblib"):
            save_data = joblib.load(path)
        else:
            raise ValueError(f"Unsupported file format: {path}")

        # Create model instance
        model_instance = cls(
            model=save_data["model"],
            preprocessor=save_data.get("preprocessor"),
            model_type=save_data.get("model_type", "classification"),
        )

        logger.info(f"Model loaded from {path}")
        return model_instance
