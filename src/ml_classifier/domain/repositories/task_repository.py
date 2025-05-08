"""Репозиторий для работы с задачами обработки."""
from abc import abstractmethod
from typing import Any, Dict, List, Optional
from uuid import UUID

from ml_classifier.domain import TaskStatus
from ml_classifier.domain.entities import Task
from ml_classifier.domain.repositories.base import Repository


class TaskRepository(Repository[Task]):
    """Интерфейс репозитория для работы с задачами обработки."""

    @abstractmethod
    async def get_by_user_id(self, user_id: UUID) -> List[Task]:
        """Получить все задачи пользователя.

        Args:
            user_id: Идентификатор пользователя

        Returns:
            List[Task]: Список задач пользователя
        """
        raise NotImplementedError

    @abstractmethod
    async def update_status(
        self, task_id: UUID, status: str, output_data: Optional[Dict] = None
    ) -> Task:
        """Обновить статус задачи и результаты.

        Args:
            task_id: Идентификатор задачи
            status: Новый статус задачи
            output_data: Результаты выполнения задачи

        Returns:
            Task: Обновленная задача
        """
        raise NotImplementedError

    @abstractmethod
    async def get_pending_tasks(self) -> List[Task]:
        """Получить все задачи в ожидании обработки.

        Returns:
            List[Task]: Список задач со статусом PENDING
        """
        raise NotImplementedError

    @abstractmethod
    async def get_by_status(self, status: TaskStatus) -> List[Task]:
        """Get tasks by status.

        Args:
            status: Task status

        Returns:
            List[Task]: List of tasks with the given status
        """
        raise NotImplementedError

    @abstractmethod
    async def get_user_tasks_count(self, user_id: UUID) -> Dict[TaskStatus, int]:
        """Get count of user's tasks by status.

        Args:
            user_id: User ID

        Returns:
            Dict[TaskStatus, int]: Dictionary with counts by status
        """
        raise NotImplementedError

    @abstractmethod
    async def mark_as_completed(self, task_id: UUID, result: Dict[str, Any]) -> Task:
        """Mark task as successfully completed.

        Args:
            task_id: Task ID
            result: Task execution result

        Returns:
            Task: Updated task
        """
        raise NotImplementedError

    @abstractmethod
    async def mark_as_failed(self, task_id: UUID, error_message: str) -> Task:
        """Mark task as failed.

        Args:
            task_id: Task ID
            error_message: Error message

        Returns:
            Task: Updated task
        """
        raise NotImplementedError
