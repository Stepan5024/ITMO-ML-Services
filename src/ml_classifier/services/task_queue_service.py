"""Service for managing task queues with priorities."""
from typing import Dict, Any, Optional
from uuid import UUID, uuid4
import time
from loguru import logger

from ml_classifier.domain.entities.enums import TaskStatus
from ml_classifier.domain.repositories.task_repository import TaskRepository
from ml_classifier.services.billing_use_cases import BillingUseCase


class TaskQueueService:
    """Service for managing ML task queues."""

    def __init__(
        self,
        task_repository: TaskRepository,
        billing_use_case: Optional[BillingUseCase] = None,
        user_task_limit: int = 10,
        max_queue_size: Dict[str, int] = None,
    ):
        """Initialize task queue service."""
        self.task_repository = task_repository
        self.billing_use_case = billing_use_case
        self.user_task_limit = user_task_limit
        self.max_queue_size = max_queue_size or {
            "low": 1000,
            "normal": 500,
            "high": 200,
        }
        self.queue_stats = {
            "low": {"avg_wait_time": 300, "current_size": 0},
            "normal": {"avg_wait_time": 120, "current_size": 0},
            "high": {"avg_wait_time": 30, "current_size": 0},
        }

    async def enqueue_task(
        self,
        task_id: UUID,
        user_id: UUID,
        model_id: UUID,
        data: Dict[str, Any],
        version_id: Optional[UUID] = None,
        priority: str = "normal",
        batch_mode: bool = False,
        sandbox: bool = False,
    ) -> str:
        """
        Add task to Celery queue with appropriate priority.

        Args:
            task_id: Task ID to track
            user_id: User ID
            model_id: Model ID to use
            data: Input data for prediction
            version_id: Optional model version ID
            priority: Task priority (low, normal, high)
            batch_mode: Whether this is a batch prediction
            sandbox: Whether to run in sandbox mode (no billing)

        Returns:
            str: Celery task ID

        Raises:
            ValueError: If queue limits are exceeded or other validation fails
        """
        operation_id = str(uuid4())
        start_time = time.time()

        logger.info(
            f"[{operation_id}] Запрос на постановку задачи в очередь: task_id={task_id}, "
            f"user_id={user_id}, priority={priority}, batch_mode={batch_mode}"
        )
        logger.debug(
            f"[{operation_id}] Параметры задачи: model_id={model_id}, "
            f"version_id={version_id if version_id else 'default'}, sandbox={sandbox}"
        )

        from ml_classifier.tasks.prediction_tasks import (
            execute_prediction,
            execute_batch_prediction,
        )

        # Check user task limits
        user_pending_tasks = await self._count_user_pending_tasks(user_id)
        logger.debug(
            f"[{operation_id}] Текущее количество задач пользователя в очереди: "
            f"{user_pending_tasks}/{self.user_task_limit}"
        )

        if user_pending_tasks >= self.user_task_limit:
            execution_time = time.time() - start_time
            logger.warning(
                f"[{operation_id}] Превышен лимит задач пользователя:"
                f" {user_pending_tasks}/{self.user_task_limit} | Время выполнения: {execution_time:.3f}с"
            )
            raise ValueError(
                f"User has too many pending tasks ({user_pending_tasks}/{self.user_task_limit})"
            )

        # Check queue size limits
        current_queue_size = self.queue_stats[priority]["current_size"]
        max_size = self.max_queue_size[priority]
        logger.debug(
            f"[{operation_id}] Текущий размер очереди '{priority}': {current_queue_size}/{max_size}"
        )

        if current_queue_size >= max_size:
            execution_time = time.time() - start_time
            logger.warning(
                f"[{operation_id}] Очередь '{priority}' заполнена: "
                f"{current_queue_size}/{max_size} | Время выполнения: {execution_time:.3f}с"
            )
            raise ValueError(f"Queue '{priority}' is at capacity")

        # Reserve funds if not in sandbox mode
        if not sandbox and self.billing_use_case:
            logger.debug(
                f"[{operation_id}] Требуется резервирование средств (не в режиме песочницы)"
            )
            # Logic for reserving funds would go here
            pass
        else:
            logger.debug(
                f"[{operation_id}] Резервирование средств не требуется (режим песочницы или биллинг отключен)"
            )

        # Select task function based on batch mode
        task_func = execute_batch_prediction if batch_mode else execute_prediction
        logger.debug(
            f"[{operation_id}] Выбрана функция обработки задачи: {'batch' if batch_mode else 'single'} prediction"
        )

        # Set queue name and priority level
        queue_name = f"ml_{priority}"
        priority_value = {"low": 1, "normal": 5, "high": 9}[priority]
        logger.debug(
            f"[{operation_id}] Параметры очереди: имя='{queue_name}', приоритет={priority_value}"
        )

        # Submit to Celery
        logger.debug(f"[{operation_id}] Отправка задачи в Celery: task_id={task_id}")
        try:
            celery_task = task_func.apply_async(
                kwargs={
                    "user_id": str(user_id),
                    "model_id": str(model_id),
                    "data": data if not batch_mode else None,
                    "data_list": data if batch_mode else None,
                    "version_id": str(version_id) if version_id else None,
                    "sandbox": sandbox,
                },
                queue=queue_name,
                priority=priority_value,
                task_id=str(task_id),
            )

            # Update queue statistics
            self.queue_stats[priority]["current_size"] += 1
            logger.debug(
                f"[{operation_id}] Размер очереди '{priority}' увеличен до {self.queue_stats[priority]['current_size']}"
            )

            execution_time = time.time() - start_time
            logger.success(
                f"[{operation_id}] Задача {task_id} успешно добавлена в очередь: celery_task_id={celery_task.id}, "
                f"очередь='{queue_name}', приоритет={priority_value} | Время выполнения: {execution_time:.3f}с"
            )

            return celery_task.id

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(
                f"[{operation_id}] Ошибка при добавлении задачи {task_id} в очередь: "
                f"{str(e)} | Время выполнения: {execution_time:.3f}с"
            )
            raise

    async def _count_user_pending_tasks(self, user_id: UUID) -> int:
        """Count pending tasks for a user."""
        operation_id = str(uuid4())
        start_time = time.time()

        logger.debug(
            f"[{operation_id}] Подсчет активных задач пользователя: user_id={user_id}"
        )

        try:
            pending_tasks = await self.task_repository.get_by_status(TaskStatus.PENDING)
            count = sum(1 for task in pending_tasks if task.user_id == user_id)

            execution_time = time.time() - start_time
            logger.debug(
                f"[{operation_id}] Количество активных задач пользователя {user_id}: "
                f"{count} | Время выполнения: {execution_time:.3f}с"
            )
            return count
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(
                f"[{operation_id}] Ошибка при подсчете активных задач пользователя "
                f"{user_id}: {str(e)} | Время выполнения: {execution_time:.3f}с"
            )
            return 0

    def check_queue_size(self) -> Dict[str, int]:
        """Get current queue sizes for all priority levels."""
        operation_id = str(uuid4())

        logger.debug(f"[{operation_id}] Запрос размеров всех очередей")

        queue_sizes = {
            priority: stats["current_size"]
            for priority, stats in self.queue_stats.items()
        }

        logger.debug(f"[{operation_id}] Текущие размеры очередей: {queue_sizes}")
        return queue_sizes

    def estimate_waiting_time(self, priority: str) -> int:
        """
        Estimate waiting time for a new task.

        Args:
            priority: Task priority

        Returns:
            int: Estimated waiting time in seconds
        """
        operation_id = str(uuid4())

        logger.debug(
            f"[{operation_id}] Оценка времени ожидания для задачи с приоритетом '{priority}'"
        )

        queue_info = self.queue_stats[priority]
        base_time = queue_info["avg_wait_time"]
        queue_size = queue_info["current_size"]

        # Simple formula considering queue size impact
        estimated_time = int(base_time * (1 + queue_size / 10))

        logger.debug(
            f"[{operation_id}] Расчет времени ожидания: приоритет='{priority}',"
            f" базовое_время={base_time}с, размер_очереди={queue_size}, оценка={estimated_time}с"
        )
        return estimated_time

    def update_queue_stats(self, priority: str, wait_time: float) -> None:
        """Update queue statistics with completed task data."""
        operation_id = str(uuid4())

        logger.debug(
            f"[{operation_id}] Обновление статистики очереди: приоритет='{priority}', время_ожидания={wait_time:.3f}с"
        )

        if priority not in self.queue_stats:
            logger.warning(
                f"[{operation_id}] Невозможно обновить статистику: очередь с приоритетом '{priority}' не найдена"
            )
            return

        # Update average wait time with exponential moving average
        stats = self.queue_stats[priority]
        old_avg = stats["avg_wait_time"]
        new_avg = old_avg * 0.9 + wait_time * 0.1
        stats["avg_wait_time"] = new_avg

        logger.debug(
            f"[{operation_id}] Среднее время ожидания обновлено: {old_avg:.3f}с -> "
            f"{new_avg:.3f}с (EMA с коэффициентом 0.1)"
        )

        # Decrease queue size
        if stats["current_size"] > 0:
            stats["current_size"] -= 1
            logger.debug(
                f"[{operation_id}] Размер очереди '{priority}' уменьшен до {stats['current_size']}"
            )
        else:
            logger.warning(
                f"[{operation_id}] Невозможно уменьшить размер очереди '{priority}': текущий размер уже 0"
            )

        logger.debug(
            f"[{operation_id}] Обновленная статистика очереди '{priority}': {stats}"
        )
