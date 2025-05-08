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

    def complete(self) -> None:
        """Mark transaction as successfully completed."""
        self.status = TransactionStatus.COMPLETED
        self.updated_at = datetime.utcnow()

    def fail(self) -> None:
        """Mark transaction as failed."""
        self.status = TransactionStatus.FAILED
        self.updated_at = datetime.utcnow()

    def is_completed(self) -> bool:
        """Check if the transaction is completed successfully.

        Returns:
            bool: True if transaction is completed successfully
        """
        return self.status == TransactionStatus.COMPLETED

    def __str__(self) -> str:
        """Представление транзакции в виде строки.

        Returns:
            str: Информация о транзакции
        """
        return f"{self.type} transaction: {self.amount} ({self.status})"
