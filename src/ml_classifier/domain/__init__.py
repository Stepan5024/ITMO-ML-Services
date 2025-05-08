# src/ml_classifier/domain/__init__.py
# src/ml_classifier/domain/__init__.py
"""Domain module for ML Classifier.

This module contains domain entities and repository interfaces
that define the business logic and data structures of the system.
"""
from ml_classifier.domain.entities.base import Entity
from ml_classifier.domain.entities.model import Model
from ml_classifier.domain.entities.role import Role, RoleType, Permission
from ml_classifier.domain.entities.task import Task, TaskStatus
from ml_classifier.domain.entities.transaction import (
    Transaction,
    TransactionStatus,
    TransactionType,
)
from ml_classifier.domain.entities.user import User

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
    "Role",
    "RoleType",
    "Permission",
]
