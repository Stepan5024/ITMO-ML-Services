"""Service for managing ML model file storage."""
import os
import uuid
from typing import Tuple, Any

import joblib


class ModelStorage:
    """Service for storing and retrieving ML model files."""

    def __init__(self, base_dir: str = "models"):
        """Initialize the storage with base directory."""
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)

    def get_model_path(self, model_id: uuid.UUID, version: str) -> str:
        """Get the file path for a specific model version."""
        model_dir = os.path.join(self.base_dir, str(model_id))
        return os.path.join(model_dir, f"{version}.joblib")

    def save_model(
        self, file_content: bytes, model_id: uuid.UUID, version: str
    ) -> Tuple[bool, str, str]:
        """
        Save a model file to storage.

        Args:
            file_content: Binary content of the model file
            model_id: Model ID
            version: Model version string

        Returns:
            Tuple[bool, str, str]: (success, message, file_path)
        """
        try:
            model_dir = os.path.join(self.base_dir, str(model_id))
            os.makedirs(model_dir, exist_ok=True)

            file_path = self.get_model_path(model_id, version)

            with open(file_path, "wb") as f:
                f.write(file_content)
            try:
                self.load_model(file_path)
            except Exception as e:
                os.remove(file_path)
                return False, f"Invalid model file: {str(e)}", ""

            return True, "Model saved successfully", file_path
        except Exception as e:
            return False, f"Failed to save model: {str(e)}", ""

    def load_model(self, file_path: str) -> Any:
        """
        Load a model from storage.

        Args:
            file_path: Path to the model file

        Returns:
            Any: The loaded model object
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Model file not found: {file_path}")

        return joblib.load(file_path)

    def delete_model(self, file_path: str) -> Tuple[bool, str]:
        """
        Delete a model file from storage.

        Args:
            file_path: Path to the model file

        Returns:
            Tuple[bool, str]: (success, message)
        """
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                return True, "Model deleted successfully"
            return False, "Model file not found"
        except Exception as e:
            return False, f"Failed to delete model: {str(e)}"

    def get_model_size(self, file_path: str) -> int:
        """
        Get the size of a model file in bytes.

        Args:
            file_path: Path to the model file

        Returns:
            int: File size in bytes
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Model file not found: {file_path}")

        return os.path.getsize(file_path)
