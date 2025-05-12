"""Доменная сущность Transaction."""
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from ml_classifier.domain.entities.base import Entity
from ml_classifier.domain.entities.enums import TransactionStatus, TransactionType


class Transaction(Entity):
    """Финансовая транзакция в системе."""

    user_id: UUID
    amount: Decimal
    type: TransactionType
    reference_id: Optional[UUID] = None
    status: TransactionStatus = TransactionStatus.PENDING
    task_id: Optional[UUID] = None
    description: Optional[str] = None
    completed_at: Optional[datetime] = None

    def complete(self) -> "Transaction":
        """Mark transaction as successfully completed."""
        return self.model_copy(
            update={
                "status": TransactionStatus.COMPLETED,
                "completed_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }
        )

    def fail(self, reason: str = None) -> "Transaction":
        """Mark transaction as failed with optional reason."""
        update = {
            "status": TransactionStatus.FAILED,
            "completed_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }

        if reason:
            new_description = (
                f"{self.description} | Failed: {reason}" if self.description else reason
            )
            update["description"] = new_description

        return self.model_copy(update=update)

    def cancel(self, reason: str = None) -> "Transaction":
        """Cancel transaction with optional reason."""
        update = {
            "status": TransactionStatus.CANCELLED,
            "completed_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }

        if reason:
            new_description = (
                f"{self.description} | Cancelled: {reason}"
                if self.description
                else reason
            )
            update["description"] = new_description

        return self.model_copy(update=update)

    def is_completed(self) -> bool:
        """Check if the transaction is completed successfully."""
        return self.status == TransactionStatus.COMPLETED

    def is_failed(self) -> bool:
        """Check if the transaction failed."""
        return self.status == TransactionStatus.FAILED

    def is_cancelled(self) -> bool:
        """Check if the transaction was cancelled."""
        return self.status == TransactionStatus.CANCELLED

    def is_final(self) -> bool:
        """Check if the transaction is in a final state (completed, failed, or cancelled)."""
        return self.is_completed() or self.is_failed() or self.is_cancelled()

    def __str__(self) -> str:
        """String representation of the transaction."""
        return f"{self.type.value} transaction: {self.amount} ({self.status.value})"
