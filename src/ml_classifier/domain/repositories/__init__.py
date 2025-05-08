"""Репозитории для работы с доменными сущностями."""
from ml_classifier.domain.repositories.base import Repository
from ml_classifier.domain.repositories.model_repository import ModelRepository
from ml_classifier.domain.repositories.task_repository import TaskRepository
from ml_classifier.domain.repositories.transaction_repository import (
    TransactionRepository,
)
from ml_classifier.domain.repositories.user_repository import UserRepository

__all__ = [
    "Repository",
    "UserRepository",
    "ModelRepository",
    "TaskRepository",
    "TransactionRepository",
]
