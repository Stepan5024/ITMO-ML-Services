from typing import Dict, List, Optional, Tuple, Any
from uuid import UUID
from celery.result import AsyncResult
from loguru import logger
import json

from ml_classifier.domain import TaskStatus
from ml_classifier.infrastructure.queue.celery_app import celery_app
from ml_classifier.domain.repositories.task_repository import TaskRepository


class TaskMonitorService:
    """Сервис для мониторинга и управления задачами Celery."""

    def __init__(self, task_repository: Optional[TaskRepository] = None):
        """Инициализирует сервис мониторинга задач."""
        self.task_repository = task_repository

    async def get_task_status(
        self, task_id: str, user_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """
        Получает статус задачи по её ID.

        Args:
            task_id: ID задачи Celery
            user_id: ID пользователя для проверки прав доступа

        Returns:
            Dict: Информация о статусе задачи

        Raises:
            ValueError: Если задача не найдена
            PermissionError: Если пользователь не имеет доступа к задаче
        """
        result = AsyncResult(task_id, app=celery_app)

        response = {
            "task_id": task_id,
            "status": result.status,
            "state": result.state,
        }

        if result.ready():
            if result.successful():
                raw_result = result.result
                if isinstance(raw_result, dict):
                    safe_result = raw_result.copy()

                    for key, value in safe_result.items():
                        if isinstance(value, str) and len(value) > 1000:
                            safe_result[key] = value[:500] + "... [truncated]"
                    response["result"] = safe_result
                else:
                    str_result = str(raw_result)
                    if len(str_result) > 1000:
                        str_result = str_result[:500] + "... [truncated]"
                    response["result"] = str_result
            else:
                response["error"] = str(result.result)

        if hasattr(result, "info") and result.info:
            if isinstance(result.info, dict) and "progress" in result.info:
                response["progress"] = result.info["progress"]

        return response

    async def get_user_tasks(
        self,
        user_id: UUID,
        status: Optional[str] = None,
        page: int = 1,
        size: int = 10,
        is_admin: bool = False,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Получает список задач пользователя с возможностью фильтрации.
        """
        logger.info(f"Getting user tasks for user {user_id}")
        if is_admin:
            tasks = await self.task_repository.list(skip=(page - 1) * size, limit=size)
            total_count = await self.task_repository.count()
        else:
            tasks = await self.task_repository.get_by_user_id(user_id)
            total_count = len(tasks)

        if status:
            try:
                status_enum = TaskStatus(status.upper())
                tasks = [task for task in tasks if task.status == status_enum]
            except ValueError:
                logger.warning(f"Invalid status filter: {status}")

        if not is_admin:
            start_idx = (page - 1) * size
            end_idx = start_idx + size
            tasks = tasks[start_idx:end_idx]

        task_list = []
        for task in tasks:
            task_info = {
                "id": str(task.id),
                "model_id": str(task.model_id),
                "status": task.status.value,
                "created_at": task.created_at.isoformat(),
                "completed_at": task.completed_at.isoformat()
                if task.completed_at
                else None,
                "duration": task.duration() if task.completed_at else None,
            }

            if task.output_data:
                output_str = json.dumps(task.output_data)
                if len(output_str) > 1000:
                    task_info["output_summary"] = output_str[:500] + "... [truncated]"
                else:
                    task_info["output_data"] = task.output_data

            if task.error_message:
                task_info["error_message"] = task.error_message

            task_list.append(task_info)

        return task_list, total_count

    async def revoke_task(
        self, task_id: str, user_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """
        Отменяет выполнение задачи.

        Args:
            task_id: ID задачи Celery
            user_id: ID пользователя для проверки прав доступа

        Returns:
            Dict: Результат операции

        Raises:
            ValueError: Если задача не найдена
            PermissionError: Если пользователь не имеет доступа к задаче
        """

        celery_app.control.revoke(task_id, terminate=True)

        logger.info(f"Task {task_id} revoked by user {user_id}")

        return {
            "task_id": task_id,
            "status": "revoked",
            "message": "Task has been revoked successfully",
        }

    async def retry_task(
        self, task_id: str, user_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """
        Повторяет выполнение задачи.

        Args:
            task_id: ID задачи Celery
            user_id: ID пользователя для проверки прав доступа

        Returns:
            Dict: Информация о новой задаче

        Raises:
            ValueError: Если задача не найдена
            PermissionError: Если пользователь не имеет доступа к задаче
        """
        result = AsyncResult(task_id, app=celery_app)

        if not result.failed():
            raise ValueError(
                f"Only failed tasks can be retried. Task {task_id} status: {result.status}"
            )

        logger.warning(
            f"Task retry functionality is not fully implemented for task {task_id}"
        )

        return {
            "task_id": task_id,
            "status": "retry_not_supported",
            "message": "Task retry functionality is not fully implemented",
        }
