"""Service for calculating prediction costs."""
from decimal import Decimal
from typing import Dict
from uuid import UUID

from ml_classifier.domain.repositories.ml_model_repository import MLModelRepository
from ml_classifier.domain.repositories.user_repository import UserRepository


class PricingService:
    """Service for calculating prediction costs."""

    def __init__(
        self,
        model_repository: MLModelRepository,
        user_repository: UserRepository,
        base_discount_percent: float = 0,
        volume_discount_threshold: int = 10,
        volume_discount_percent: float = 5,
        text_size_threshold: int = 1000,
        text_complexity_factor: float = 1.2,
    ):
        """
        Initialize pricing service with repositories and pricing parameters.

        Args:
            model_repository: Repository for ML models
            user_repository: Repository for users
            base_discount_percent: Base discount percentage for all users
            volume_discount_threshold: Batch size threshold for volume discounts
            volume_discount_percent: Discount percentage for volume orders
            text_size_threshold: Threshold for text size complexity pricing
            text_complexity_factor: Multiplier for complex text
        """
        self.model_repository = model_repository
        self.user_repository = user_repository
        self.base_discount_percent = base_discount_percent
        self.volume_discount_threshold = volume_discount_threshold
        self.volume_discount_percent = volume_discount_percent
        self.text_size_threshold = text_size_threshold
        self.text_complexity_factor = text_complexity_factor

    async def calculate_prediction_cost(
        self,
        model_id: UUID,
        input_data: Dict,
        batch_size: int = 1,
        priority: str = "normal",
    ) -> Dict:
        """
        Calculate cost for a prediction.

        Args:
            model_id: Model ID
            input_data: Input data for prediction
            batch_size: Number of items in batch
            priority: Priority level ("normal" or "high")

        Returns:
            Dict: Cost details

        Raises:
            ValueError: If model not found
        """
        model = await self.model_repository.get_by_id(model_id)
        if not model:
            raise ValueError(f"Model with ID {model_id} not found")

        base_price = model.price_per_call

        complexity_factor = Decimal(str(self._calculate_complexity_factor(input_data)))

        priority_factor = Decimal(str(self._calculate_priority_factor(priority)))

        volume_discount = self._calculate_volume_discount(batch_size, base_price)

        batch_size_decimal = Decimal(str(batch_size))

        base_cost = (
            base_price * complexity_factor * priority_factor * batch_size_decimal
        )

        discounted_cost = base_cost - volume_discount

        if base_cost > Decimal("0"):
            discount_percentage = (volume_discount / base_cost) * Decimal("100")
        else:
            discount_percentage = Decimal("0")

        return {
            "base_cost": float(base_cost),
            "discounted_cost": float(discounted_cost),
            "discount_percentage": float(discount_percentage),
            "currency": "USD",
            "breakdown": {
                "model_base_price": float(base_price),
                "complexity_factor": float(complexity_factor),
                "priority_factor": float(priority_factor),
                "volume_discount": float(volume_discount),
                "batch_size": batch_size,
            },
        }

    async def apply_discounts(self, user_id: UUID, base_cost: Decimal) -> Decimal:
        """
        Apply user-specific discounts to base cost.

        Args:
            user_id: User ID
            base_cost: Base cost before discounts

        Returns:
            Decimal: Discounted cost
        """
        discount = (base_cost * self.base_discount_percent) / Decimal("100")
        return base_cost - discount

    async def calculate_batch_cost(
        self, model_id: UUID, batch_size: int, priority: str = "normal"
    ) -> Decimal:
        """
        Calculate cost for batch prediction.

        Args:
            model_id: Model ID
            batch_size: Number of items in batch
            priority: Priority level ("normal" or "high")

        Returns:
            Decimal: Total cost for batch

        Raises:
            ValueError: If model not found
        """
        model = await self.model_repository.get_by_id(model_id)
        if not model:
            raise ValueError(f"Model with ID {model_id} not found")

        batch_size_decimal = Decimal(str(batch_size))
        base_cost = model.price_per_call * batch_size_decimal

        priority_factor = Decimal(str(self._calculate_priority_factor(priority)))
        base_cost = base_cost * priority_factor

        volume_discount = self._calculate_volume_discount(
            batch_size, model.price_per_call
        )

        return base_cost - volume_discount

    def _calculate_complexity_factor(self, input_data: Dict) -> float:
        """
        Calculate complexity factor based on input data.

        Args:
            input_data: Input data for prediction

        Returns:
            float: Complexity factor
        """
        if "text" in input_data and isinstance(input_data["text"], str):
            text_length = len(input_data["text"])
            if text_length > self.text_size_threshold:
                return float(self.text_complexity_factor)
        return 1.0

    def _calculate_priority_factor(self, priority: str) -> float:
        """
        Calculate factor based on priority level.

        Args:
            priority: Priority level ("normal" or "high")

        Returns:
            float: Priority factor
        """
        if priority.lower() == "high":
            return 1.5
        return 1.0

    def _calculate_volume_discount(
        self, batch_size: int, base_price: Decimal
    ) -> Decimal:
        """
        Calculate discount for batch volume.

        Args:
            batch_size: Number of items in batch
            base_price: Base price per item

        Returns:
            Decimal: Total discount amount
        """
        batch_size_decimal = Decimal(str(batch_size))
        if batch_size >= self.volume_discount_threshold:
            discount_multiplier = self.volume_discount_percent / Decimal("100")
            return base_price * batch_size_decimal * discount_multiplier
        return Decimal("0")
