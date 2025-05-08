"""Доменная сущность Task."""
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from ml_classifier.domain.entities.base import Entity
from ml_classifier.domain.entities.enums import TaskStatus


class Task(Entity):
    """Задача обработки данных моделью ML."""

    user_id: UUID
    model_id: UUID
    status: TaskStatus = TaskStatus.PENDING
    input_data: Dict[str, Any]
    output_data: Optional[Dict[str, Any]] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None

    def is_completed(self) -> bool:
        """Проверить, завершена ли задача.

        Returns:
            bool: True, если задача завершена успешно
        """
        return self.status == TaskStatus.COMPLETED

    def is_failed(self) -> bool:
        """Check if the task failed.

        Returns:
            bool: True if task failed
        """
        return self.status == TaskStatus.FAILED

    def duration(self) -> Optional[float]:
        """Вычислить длительность выполнения задачи в секундах.

        Returns:
            Optional[float]: Длительность в секундах или None, если задача не завершена
        """
        if not self.completed_at:
            return None

        delta = self.completed_at - self.created_at
        return delta.total_seconds()

    def complete(self, result: Dict[str, Any]) -> None:
        """Mark task as successfully completed.

        Args:
            result: Task execution result
        """
        self.status = TaskStatus.COMPLETED
        self.result = result
        self.output_data = result
        self.completed_at = datetime.utcnow()
        self.updated_at = self.completed_at

    def fail(self, error_message: str) -> None:
        """Mark task as failed.

        Args:
            error_message: Error message
        """
        self.status = TaskStatus.FAILED
        self.error_message = error_message
        self.completed_at = datetime.utcnow()
        self.updated_at = self.completed_at
