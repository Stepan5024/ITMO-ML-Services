"""Balance entity for user account balance."""
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import Field, validator

from ml_classifier.domain.entities.base import Entity


class Balance(Entity):
    """User account balance entity."""

    user_id: UUID
    amount: Decimal = Field(default=Decimal("0.0"), ge=0)
    last_updated: datetime = Field(default_factory=datetime.utcnow)

    @validator("amount")
    def amount_not_negative(cls, v):
        """Validate that balance is not negative."""
        if v < 0:
            raise ValueError("Balance cannot be negative")
        return v

    def has_sufficient_funds(self, amount: Decimal) -> bool:
        """Check if the balance has sufficient funds for a transaction."""
        return self.amount >= amount

    def update(self, delta: Decimal) -> "Balance":
        """
        Update balance by adding delta amount (can be negative for deductions).

        Args:
            delta: Amount to add to balance (negative for deductions)

        Returns:
            Self for method chaining

        Raises:
            ValueError: If the resulting balance would be negative
        """
        new_amount = self.amount + delta
        if new_amount < 0:
            raise ValueError(
                f"Insufficient funds: {self.amount} + {delta} = {new_amount}"
            )

        self.amount = new_amount
        self.last_updated = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        return self

    def __str__(self) -> str:
        """String representation of the balance."""
        return f"Balance: {self.amount}"
