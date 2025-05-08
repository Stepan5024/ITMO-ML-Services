# src/ml_classifier/infrastructure/db/__init__.py
"""Database implementation for the ML classifier."""
from ml_classifier.infrastructure.db.database import (
    Base,
    check_database_connection,
    get_db,
    init_db,
)
from ml_classifier.infrastructure.db.models import Model, Task, Transaction, User
from ml_classifier.infrastructure.db.repositories import (
    SQLAlchemyModelRepository,
    SQLAlchemyTaskRepository,
    SQLAlchemyTransactionRepository,
    SQLAlchemyUserRepository,
)

__all__ = [
    # Database utilities
    "Base",
    "get_db",
    "init_db",
    "check_database_connection",
    # Repository implementations
    "SQLAlchemyUserRepository",
    "SQLAlchemyModelRepository",
    "SQLAlchemyTaskRepository",
    "SQLAlchemyTransactionRepository",
    # Database models
    "User",
    "Model",
    "Task",
    "Transaction",
]
