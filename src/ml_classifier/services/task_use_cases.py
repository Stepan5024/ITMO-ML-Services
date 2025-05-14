"""Business logic for task operations."""
from datetime import datetime
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
        # Validate model exists
        model = await self.model_repository.get_by_id(model_id)
        if not model:
            return False, f"Model with ID {model_id} not found", None

        # Validate model is active
        if not model.is_active:
            return False, f"Model {model.name} is inactive", None

        # Check balance if not sandbox mode
        if not sandbox and self.billing_use_case:
            balance = await self.billing_use_case.get_balance(user_id)
            if balance < model.price_per_call:
                return False, "Insufficient balance", None

        # Create task entity
        task = Task(
            id=uuid4(),
            user_id=user_id,
            model_id=model_id,
            input_data=input_data,
            status=TaskStatus.PENDING,
            priority=priority,
            model_version_id=model_version_id,
            created_at=datetime.utcnow(),
        )

        # Save task to repository
        created_task = await self.task_repository.create(task)

        try:
            # Enqueue task
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
            created_task.celery_task_id = celery_task_id
            await self.task_repository.update(created_task)

            return True, "Task created and queued successfully", created_task

        except Exception as e:
            # Attempt to delete the task if queuing fails
            try:
                await self.task_repository.delete(created_task.id)
            except Exception as cleanup_error:
                logger.error(
                    f"Failed to delete task after enqueue failure: {cleanup_error}"
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
        task = await self.task_repository.get_by_id(task_id)
        if not task:
            return False, f"Task with ID {task_id} not found", None

        # Check permissions (user must own the task or be an admin)
        if task.user_id != user_id and not allow_admin:
            return False, "You don't have permission to access this task", None

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
        # Get task with permission check
        success, message, task = await self.get_task(user_id, task_id)
        if not success:
            return False, message, None

        # Only pending tasks can be cancelled
        if task.status != TaskStatus.PENDING:
            return False, f"Cannot cancel task with status {task.status.value}", None

        from ml_classifier.infrastructure.queue.celery_app import celery_app

        # Attempt to revoke the Celery task
        if task.celery_task_id:
            celery_app.control.revoke(task.celery_task_id, terminate=True)

        # Update task status
        task.fail("Task cancelled by user")
        updated_task = await self.task_repository.update(task)

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
        pagination = {"page": page, "size": size}
        return await self.task_repository.list_by_user(user_id, filters, pagination)

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
        # Get counts by status
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

        total_count = pending_count + processing_count + completed_count + failed_count

        success_rate = 0
        if completed_count + failed_count > 0:
            success_rate = (completed_count / (completed_count + failed_count)) * 100

        # Calculate average times
        # This would need a separate method to get average times from the repository
        avg_processing_time = 0  # placeholder - implement this functionality
        avg_waiting_time = 0  # placeholder - implement this functionality

        return {
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
        # Get original task with permission check
        success, message, original_task = await self.get_task(user_id, task_id)
        if not success:
            return False, message, None

        # Only failed tasks can be rerun
        if original_task.status != TaskStatus.FAILED:
            return (
                False,
                f"Only failed tasks can be rerun. Current status: {original_task.status.value}",
                None,
            )

        # Create new task with same parameters
        return await self.create_task(
            user_id=user_id,
            model_id=original_task.model_id,
            input_data=original_task.input_data,
            priority=original_task.priority,
            model_version_id=original_task.model_version_id,
            sandbox=False,
        )
