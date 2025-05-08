"""Database models for the ML classifier service (SQLAlchemy 1.x compatible)."""
import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, relationship

from ml_classifier.domain.entities import TaskStatus, TransactionStatus, TransactionType
from ml_classifier.infrastructure.db.database import Base


class User(Base):
    """Модель пользователя в базе данных."""

    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)
    balance = Column(Numeric(10, 2), nullable=False, default=0.0)
    is_active = Column(Boolean, default=True, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Отношения
    tasks: Mapped[list["Task"]] = relationship(
        "Task", back_populates="user", cascade="all, delete-orphan"
    )  # type: ignore
    transactions: Mapped[list["Transaction"]] = relationship(
        "Transaction", back_populates="user", cascade="all, delete-orphan"
    )  # type: ignore


class Model(Base):
    """Модель ML-модели в базе данных."""

    __tablename__ = "models"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, unique=True, nullable=False, index=True)
    description = Column(Text)
    version = Column(String, nullable=False)
    input_schema = Column(JSONB, default={})
    output_schema = Column(JSONB, default={})
    price_per_request = Column(Numeric(10, 2), nullable=False, default=0.0)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Отношения
    tasks: Mapped[list["Task"]] = relationship(
        "Task", back_populates="model", cascade="all, delete-orphan"
    )  # type: ignore


class Task(Base):
    """Модель задачи классификации в базе данных."""

    __tablename__ = "tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    model_id = Column(
        UUID(as_uuid=True), ForeignKey("models.id"), nullable=False, index=True
    )
    input_text = Column(Text, nullable=False)
    result = Column(JSONB)
    error_message = Column(Text)
    status = Column(
        Enum(TaskStatus), default=TaskStatus.PENDING, nullable=False, index=True
    )
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    completed_at = Column(DateTime)

    # Отношения
    user: Mapped["User"] = relationship("User", back_populates="tasks")
    model: Mapped["Model"] = relationship("Model", back_populates="tasks")

    transactions: Mapped[List["Transaction"]] = relationship(
        "Transaction", back_populates="task", cascade="all, delete-orphan"
    )  # type: ignore


class Transaction(Base):
    """Модель транзакции в базе данных."""

    __tablename__ = "transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    amount = Column(Numeric(10, 2), nullable=False)
    type = Column(Enum(TransactionType), nullable=False, index=True)
    reference_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=True)
    description = Column(String)
    status = Column(
        Enum(TransactionStatus), default=TransactionStatus.PENDING, nullable=False
    )
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Отношения
    user: Mapped["User"] = relationship("User", back_populates="transactions")
    task: Mapped[Optional["Task"]] = relationship("Task", back_populates="transactions")
