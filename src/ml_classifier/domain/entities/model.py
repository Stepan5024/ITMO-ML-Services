"""Доменная сущность Model."""
from decimal import Decimal
from typing import Any, Dict, Optional

from pydantic import Field

from ml_classifier.domain.entities.base import Entity


class Model(Entity):
    """ML модель для классификации отзывов."""

    name: str
    description: Optional[str] = None
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    is_active: bool = True
    price_per_call: Decimal = Field(default=Decimal("0.0"), ge=0)
    version: str = "1.0.0"

    def validate_input_data(self, input_data: Dict[str, Any]) -> bool:
        """Проверить входные данные на соответствие схеме.

        Args:
            input_data: Входные данные для модели

        Returns:
            bool: True, если данные соответствуют схеме
        """
        required_fields = [
            field
            for field, schema in self.input_schema.items()
            if schema.get("required", False)
        ]
        return all(field in input_data for field in required_fields)

    def __str__(self) -> str:
        """Представление модели в виде строки.

        Returns:
            str: Информация о модели
        """
        return f"{self.name} (v{self.version})"
