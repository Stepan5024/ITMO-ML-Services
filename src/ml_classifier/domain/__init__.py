# src/ml_classifier/domain/__init__.py
"""Domain module for ML Classifier.

This module contains domain entities and repository interfaces
that define the business logic and data structures of the system.
"""

# Import all entities
from ml_classifier.domain.entities import (
    Entity,
    Model,
    Task,
    TaskStatus,
    Transaction,
    TransactionStatus,
    TransactionType,
    User,
)

# Import all repository interfaces
from ml_classifier.domain.repositories import (
    ModelRepository,
    Repository,
    TaskRepository,
    TransactionRepository,
    UserRepository,
)

__all__ = [
    # Entities
    "Entity",
    "User",
    "Model",
    "Task",
    "TaskStatus",
    "Transaction",
    "TransactionType",
    "TransactionStatus",
    # Repositories
    "Repository",
    "UserRepository",
    "ModelRepository",
    "TaskRepository",
    "TransactionRepository",
]
