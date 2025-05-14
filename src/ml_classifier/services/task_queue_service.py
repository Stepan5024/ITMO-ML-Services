"""Service for managing task queues with priorities."""
from typing import Dict, Any, Optional
from uuid import UUID
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
        from ml_classifier.tasks.prediction_tasks import (
            execute_prediction,
            execute_batch_prediction,
        )

        # Check user task limits
        user_pending_tasks = await self._count_user_pending_tasks(user_id)
        if user_pending_tasks >= self.user_task_limit:
            raise ValueError(
                f"User has too many pending tasks ({user_pending_tasks}/{self.user_task_limit})"
            )

        # Check queue size limits
        if self.queue_stats[priority]["current_size"] >= self.max_queue_size[priority]:
            raise ValueError(f"Queue '{priority}' is at capacity")

        # Reserve funds if not in sandbox mode
        if not sandbox and self.billing_use_case:
            # Logic for reserving funds would go here
            pass

        # Select task function based on batch mode
        task_func = execute_batch_prediction if batch_mode else execute_prediction

        # Set queue name and priority level
        queue_name = f"ml_{priority}"
        priority_value = {"low": 1, "normal": 5, "high": 9}[priority]

        # Submit to Celery
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

        logger.info(
            f"Task {task_id} enqueued with celery_task_id {celery_task.id} "
            f"in queue '{queue_name}' with priority {priority_value}"
        )

        return celery_task.id

    async def _count_user_pending_tasks(self, user_id: UUID) -> int:
        """Count pending tasks for a user."""
        pending_tasks = await self.task_repository.get_by_status(TaskStatus.PENDING)
        return sum(1 for task in pending_tasks if task.user_id == user_id)

    def check_queue_size(self) -> Dict[str, int]:
        """Get current queue sizes for all priority levels."""
        return {
            priority: stats["current_size"]
            for priority, stats in self.queue_stats.items()
        }

    def estimate_waiting_time(self, priority: str) -> int:
        """
        Estimate waiting time for a new task.

        Args:
            priority: Task priority

        Returns:
            int: Estimated waiting time in seconds
        """
        queue_info = self.queue_stats[priority]
        base_time = queue_info["avg_wait_time"]
        queue_size = queue_info["current_size"]

        # Simple formula considering queue size impact
        return int(base_time * (1 + queue_size / 10))

    def update_queue_stats(self, priority: str, wait_time: float) -> None:
        """Update queue statistics with completed task data."""
        if priority not in self.queue_stats:
            return

        # Update average wait time with exponential moving average
        stats = self.queue_stats[priority]
        old_avg = stats["avg_wait_time"]
        stats["avg_wait_time"] = old_avg * 0.9 + wait_time * 0.1

        # Decrease queue size
        if stats["current_size"] > 0:
            stats["current_size"] -= 1
