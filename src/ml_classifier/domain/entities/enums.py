# src/ml_classifier/domain/entities/enums.py
from enum import Enum


class TaskStatus(str, Enum):
    """Task processing statuses."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class TransactionType(str, Enum):
    """Transaction types."""

    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    CHARGE = "charge"
    TASK_PAYMENT = "task_payment"


class TransactionStatus(str, Enum):
    """Transaction statuses."""

    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
