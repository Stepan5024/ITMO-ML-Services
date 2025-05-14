"""Business logic for task operations."""
from datetime import datetime
import time
from typing import Dict, List, Optional, Tuple, Any
from uuid import UUID, uuid4

from loguru import logger

from ml_classifier.domain.entities.enums import TaskStatus
from ml_classifier.domain.entities.task import Task
from ml_classifier.domain.repositories.task_repository import TaskRepository
from ml_classifier.domain.repositories.ml_model_repository import MLModelRepository
from ml_classifier.services.task_queue_service import TaskQueueService
from ml_classifier.services.billing_use_cases import BillingUseCase


class TaskUseCase:
    """Use case for task operations."""

    def __init__(
        self,
        task_repository: TaskRepository,
        model_repository: MLModelRepository,
        task_queue_service: TaskQueueService,
        billing_use_case: Optional[BillingUseCase] = None,
    ):
        """Initialize task use case."""
        self.task_repository = task_repository
        self.model_repository = model_repository
        self.task_queue_service = task_queue_service
        self.billing_use_case = billing_use_case

    async def create_task(
        self,
        user_id: UUID,
        model_id: UUID,
        input_data: Dict[str, Any],
        priority: str = "normal",
        model_version_id: Optional[UUID] = None,
        sandbox: bool = False,
    ) -> Tuple[bool, str, Optional[Task]]:
        """
        Create and enqueue a classification task.

        Args:
            user_id: User ID
            model_id: Model ID
            input_data: Data for classification
            priority: Task priority (low, normal, high)
            model_version_id: Optional specific model version
            sandbox: Whether to run in sandbox mode (no billing)

        Returns:
            Tuple[bool, str, Optional[Task]]: (success, message, created task)
        """
        operation_id = str(uuid4())
        start_time = time.time()

        logger.info(
            f"[{operation_id}] Создание задачи: user_id={user_id}, model_id={model_id},"
            f" priority={priority}, model_version_id={model_version_id}, sandbox={sandbox}"
        )
        logger.debug(
            f"[{operation_id}] Размер входных данных: {len(str(input_data))} символов"
        )

        model = await self.model_repository.get_by_id(model_id)
        if not model:
            logger.warning(f"[{operation_id}] Модель с ID {model_id} не найдена")
            return False, f"Model with ID {model_id} not found", None

        logger.debug(
            f"[{operation_id}] Найдена модель: {model.name}, тип: {model.model_type}, активна: {model.is_active}"
        )

        # Validate model is active
        if not model.is_active:
            logger.warning(
                f"[{operation_id}] Модель {model.name} неактивна, создание задачи невозможно"
            )
            return False, f"Model {model.name} is inactive", None

        # Check balance if not sandbox mode
        if not sandbox and self.billing_use_case:
            logger.debug(f"[{operation_id}] Проверка баланса пользователя: {user_id}")
            balance = await self.billing_use_case.get_balance(user_id)
            if balance < model.price_per_call:
                logger.warning(
                    f"[{operation_id}] Недостаточно средств: баланс={float(balance)}, "
                    f"требуется={float(model.price_per_call)}"
                )
                return False, "Insufficient balance", None
            logger.debug(
                f"[{operation_id}] Баланс достаточен: {float(balance)} > {float(model.price_per_call)}"
            )

        # Create task entity
        task_id = uuid4()
        logger.debug(f"[{operation_id}] Создание сущности задачи с ID: {task_id}")
        task = Task(
            id=task_id,
            user_id=user_id,
            model_id=model_id,
            input_data=input_data,
            status=TaskStatus.PENDING,
            priority=priority,
            model_version_id=model_version_id,
            created_at=datetime.utcnow(),
        )

        # Save task to repository
        logger.debug(f"[{operation_id}] Сохранение задачи в репозиторий: {task_id}")
        created_task = await self.task_repository.create(task)

        try:
            # Enqueue task
            logger.debug(
                f"[{operation_id}] Постановка задачи {task_id} в очередь: priority={priority}"
            )
            celery_task_id = await self.task_queue_service.enqueue_task(
                task_id=created_task.id,
                user_id=user_id,
                model_id=model_id,
                data=input_data,
                version_id=model_version_id,
                priority=priority,
                batch_mode=False,
                sandbox=sandbox,
            )

            # Update task with Celery ID
            logger.debug(
                f"[{operation_id}] Задача поставлена в очередь. Celery task ID: {celery_task_id}"
            )
            created_task.celery_task_id = celery_task_id
            await self.task_repository.update(created_task)

            execution_time = time.time() - start_time
            logger.success(
                f"[{operation_id}] Задача успешно создана и поставлена в очередь: ID={task_id},"
                f" Celery ID={celery_task_id} | Время выполнения: {execution_time:.3f}с"
            )
            return True, "Task created and queued successfully", created_task

        except Exception as e:
            # Attempt to delete the task if queuing fails
            logger.error(
                f"[{operation_id}] Ошибка при постановке задачи {task_id} в очередь: {str(e)}"
            )
            try:
                logger.debug(
                    f"[{operation_id}] Попытка удаления неудавшейся задачи: {task_id}"
                )
                await self.task_repository.delete(created_task.id)
                logger.debug(
                    f"[{operation_id}] Задача {task_id} успешно удалена после сбоя"
                )
            except Exception as cleanup_error:
                logger.error(
                    f"[{operation_id}] Ошибка при удалении задачи {task_id} после сбоя: {cleanup_error}"
                )

            execution_time = time.time() - start_time
            logger.error(
                f"[{operation_id}] Создание задачи не удалось | Время выполнения: {execution_time:.3f}с"
            )
            return False, f"Error queuing task: {str(e)}", None

    async def get_task(
        self, user_id: UUID, task_id: UUID, allow_admin: bool = False
    ) -> Tuple[bool, str, Optional[Task]]:
        """
        Get task by ID with permission check.

        Args:
            user_id: User ID requesting the task
            task_id: Task ID to retrieve
            allow_admin: Whether admins can access tasks from other users

        Returns:
            Tuple[bool, str, Optional[Task]]: (success, message, task)
        """
        operation_id = str(uuid4())
        start_time = time.time()

        logger.info(
            f"[{operation_id}] Запрос задачи: task_id={task_id}, requestor_id={user_id}, allow_admin={allow_admin}"
        )

        task = await self.task_repository.get_by_id(task_id)
        if not task:
            execution_time = time.time() - start_time
            logger.warning(
                f"[{operation_id}] Задача с ID {task_id} не найдена | Время выполнения: {execution_time:.3f}с"
            )
            return False, f"Task with ID {task_id} not found", None

        logger.debug(
            f"[{operation_id}] Найдена задача: ID={task_id}, user_id={task.user_id}, "
            f"status={task.status.value}, приоритет={task.priority}"
        )

        # Check permissions (user must own the task or be an admin)
        if task.user_id != user_id and not allow_admin:
            execution_time = time.time() - start_time
            logger.warning(
                f"[{operation_id}] Отказ в доступе: пользователь {user_id} "
                f"пытается получить доступ к задаче пользователя {task.user_id} "
                f"| Время выполнения: {execution_time:.3f}с"
            )
            return False, "You don't have permission to access this task", None

        execution_time = time.time() - start_time
        logger.success(
            f"[{operation_id}] Задача успешно получена: ID={task_id},"
            f" status={task.status.value} | Время выполнения: {execution_time:.3f}с"
        )
        return True, "Task retrieved successfully", task

    async def cancel_task(
        self, user_id: UUID, task_id: UUID
    ) -> Tuple[bool, str, Optional[Task]]:
        """
        Cancel a pending task.

        Args:
            user_id: User ID requesting cancellation
            task_id: Task ID to cancel

        Returns:
            Tuple[bool, str, Optional[Task]]: (success, message, updated task)
        """
        operation_id = str(uuid4())
        start_time = time.time()

        logger.info(
            f"[{operation_id}] Запрос на отмену задачи: task_id={task_id}, user_id={user_id}"
        )

        # Get task with permission check
        success, message, task = await self.get_task(user_id, task_id)
        if not success:
            execution_time = time.time() - start_time
            logger.warning(
                f"[{operation_id}] Невозможно отменить задачу: {message} | Время выполнения: {execution_time:.3f}с"
            )
            return False, message, None

        logger.debug(
            f"[{operation_id}] Проверка возможности отмены задачи: ID={task_id}, текущий статус={task.status.value}"
        )

        # Only pending tasks can be cancelled
        if task.status != TaskStatus.PENDING:
            execution_time = time.time() - start_time
            logger.warning(
                f"[{operation_id}] Невозможно отменить задачу со статусом"
                f" {task.status.value} | Время выполнения: {execution_time:.3f}с"
            )
            return False, f"Cannot cancel task with status {task.status.value}", None

        from ml_classifier.infrastructure.queue.celery_app import celery_app

        # Attempt to revoke the Celery task
        if task.celery_task_id:
            logger.debug(
                f"[{operation_id}] Отмена задачи Celery: {task.celery_task_id}"
            )
            celery_app.control.revoke(task.celery_task_id, terminate=True)
        else:
            logger.debug(
                f"[{operation_id}] У задачи {task_id} отсутствует ID задачи Celery"
            )

        # Update task status
        logger.debug(
            f"[{operation_id}] Изменение статуса задачи {task_id} на FAILED с причиной: отмена пользователем"
        )
        task.fail("Task cancelled by user")
        updated_task = await self.task_repository.update(task)

        execution_time = time.time() - start_time
        logger.success(
            f"[{operation_id}] Задача успешно отменена: ID={task_id} | Время выполнения: {execution_time:.3f}с"
        )
        return True, "Task cancelled successfully", updated_task

    async def list_user_tasks(
        self, user_id: UUID, filters: Dict, page: int, size: int
    ) -> Tuple[List[Task], int]:
        """
        Get list of tasks for a user with filtering and pagination.

        Args:
            user_id: User ID
            filters: Filter parameters
            page: Page number
            size: Page size

        Returns:
            Tuple[List[Task], int]: (tasks list, total count)
        """
        operation_id = str(uuid4())
        start_time = time.time()

        logger.info(
            f"[{operation_id}] Запрос списка задач пользователя: user_id={user_id}, page={page}, size={size}"
        )
        logger.debug(f"[{operation_id}] Фильтры для списка задач: {filters}")

        pagination = {"page": page, "size": size}
        try:
            tasks, total = await self.task_repository.list_by_user(
                user_id, filters, pagination
            )

            execution_time = time.time() - start_time
            logger.success(
                f"[{operation_id}] Получен список задач пользователя: user_id={user_id}, "
                f"получено={len(tasks)}, всего={total} | Время выполнения: {execution_time:.3f}с"
            )

            if tasks:
                status_counts = {}
                for task in tasks:
                    status = task.status.value
                    status_counts[status] = status_counts.get(status, 0) + 1
                logger.debug(
                    f"[{operation_id}] Распределение задач по статусам: {status_counts}"
                )

            return tasks, total
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(
                f"[{operation_id}] Ошибка при получении списка задач пользователя "
                f"{user_id}: {str(e)} | Время выполнения: {execution_time:.3f}с"
            )
            return [], 0

    async def get_task_statistics(
        self, user_id: UUID, from_date: datetime, to_date: datetime
    ) -> Dict:
        """
        Get task statistics for a user in a date range.

        Args:
            user_id: User ID
            from_date: Start date
            to_date: End date

        Returns:
            Dict: Statistics about tasks
        """
        operation_id = str(uuid4())
        start_time = time.time()

        logger.info(
            f"[{operation_id}] Запрос статистики задач: user_id={user_id}, "
            f"from={from_date.isoformat()}, to={to_date.isoformat()}"
        )

        try:
            # Get counts by status
            logger.debug(f"[{operation_id}] Получение количества задач по статусам")
            pending_count = await self.task_repository.count_by_status_and_date(
                TaskStatus.PENDING, from_date, to_date
            )
            processing_count = await self.task_repository.count_by_status_and_date(
                TaskStatus.PROCESSING, from_date, to_date
            )
            completed_count = await self.task_repository.count_by_status_and_date(
                TaskStatus.COMPLETED, from_date, to_date
            )
            failed_count = await self.task_repository.count_by_status_and_date(
                TaskStatus.FAILED, from_date, to_date
            )

            total_count = (
                pending_count + processing_count + completed_count + failed_count
            )
            logger.debug(
                f"[{operation_id}] Всего задач: {total_count} (в процессе:"
                f" {pending_count + processing_count}, завершено: {completed_count}, ошибки: {failed_count})"
            )

            success_rate = 0
            if completed_count + failed_count > 0:
                success_rate = (
                    completed_count / (completed_count + failed_count)
                ) * 100
                logger.debug(
                    f"[{operation_id}] Успешность выполнения задач: {success_rate:.2f}%"
                )

            avg_processing_time = 0
            avg_waiting_time = 0

            stats = {
                "total_count": total_count,
                "status_counts": {
                    "pending": pending_count,
                    "processing": processing_count,
                    "completed": completed_count,
                    "failed": failed_count,
                },
                "success_rate": success_rate,
                "avg_processing_time_ms": avg_processing_time,
                "avg_waiting_time_ms": avg_waiting_time,
                "period": {"from": from_date.isoformat(), "to": to_date.isoformat()},
            }

            execution_time = time.time() - start_time
            logger.success(
                f"[{operation_id}] Статистика задач успешно получена: user_id={user_id},"
                f" всего задач={total_count} | Время выполнения: {execution_time:.3f}с"
            )

            return stats
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(
                f"[{operation_id}] Ошибка при получении статистики задач пользователя {user_id}: "
                f"{str(e)} | Время выполнения: {execution_time:.3f}с"
            )

            return {
                "total_count": 0,
                "status_counts": {
                    "pending": 0,
                    "processing": 0,
                    "completed": 0,
                    "failed": 0,
                },
                "success_rate": 0,
                "avg_processing_time_ms": 0,
                "avg_waiting_time_ms": 0,
                "period": {"from": from_date.isoformat(), "to": to_date.isoformat()},
                "error": str(e),
            }

    async def rerun_failed_task(
        self, user_id: UUID, task_id: UUID
    ) -> Tuple[bool, str, Optional[Task]]:
        """
        Rerun a failed task.

        Args:
            user_id: User ID requesting the rerun
            task_id: Task ID to rerun

        Returns:
            Tuple[bool, str, Optional[Task]]: (success, message, new task)
        """
        operation_id = str(uuid4())
        start_time = time.time()

        logger.info(
            f"[{operation_id}] Запрос на повторный запуск задачи: task_id={task_id}, user_id={user_id}"
        )

        # Get original task with permission check
        success, message, original_task = await self.get_task(user_id, task_id)
        if not success:
            execution_time = time.time() - start_time
            logger.warning(
                f"[{operation_id}] Невозможно перезапустить задачу: {message} | Время выполнения: {execution_time:.3f}с"
            )
            return False, message, None

        logger.debug(
            f"[{operation_id}] Найдена задача для перезапуска: ID={task_id}, status={original_task.status.value}"
        )

        # Only failed tasks can be rerun
        if original_task.status != TaskStatus.FAILED:
            execution_time = time.time() - start_time
            logger.warning(
                f"[{operation_id}] Невозможно перезапустить задачу со статусом "
                f"{original_task.status.value} | Время выполнения: {execution_time:.3f}с"
            )
            return (
                False,
                f"Only failed tasks can be rerun. Current status: {original_task.status.value}",
                None,
            )

        logger.debug(
            f"[{operation_id}] Подготовка к созданию новой задачи на основе {task_id}:"
            f" model_id={original_task.model_id}, priority={original_task.priority}"
        )

        # Create new task with same parameters
        success, message, new_task = await self.create_task(
            user_id=user_id,
            model_id=original_task.model_id,
            input_data=original_task.input_data,
            priority=original_task.priority,
            model_version_id=original_task.model_version_id,
            sandbox=False,
        )

        if success:
            execution_time = time.time() - start_time
            logger.success(
                f"[{operation_id}] Задача успешно перезапущена: старый ID={task_id}, "
                f"новый ID={new_task.id} | Время выполнения: {execution_time:.3f}с"
            )
        else:
            execution_time = time.time() - start_time
            logger.error(
                f"[{operation_id}] Ошибка при перезапуске задачи {task_id}: {message} "
                f"| Время выполнения: {execution_time:.3f}с"
            )

        return success, message, new_task
