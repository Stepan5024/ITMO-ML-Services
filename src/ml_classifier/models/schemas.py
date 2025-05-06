# File: ITMO-ML-Services/src/ml_classifier/models/schemas.py
"""Common schema models for the application."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """Error response model."""

    status_code: int
    message: str
    error_type: str
    errors: Optional[List[Dict[str, Any]]] = None
