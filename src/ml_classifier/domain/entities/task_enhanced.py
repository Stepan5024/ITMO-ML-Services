"""Enhanced domain entity for task management."""
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from ml_classifier.domain.entities.base import Entity
from ml_classifier.domain.entities.enums import TaskStatus


class TaskPriority:
    """Task priority levels."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


class EnhancedTask(Entity):
    """Task entity for processing classification requests."""

    user_id: UUID
    model_id: UUID
    status: TaskStatus = TaskStatus.PENDING
    input_data: Dict[str, Any]
    output_data: Optional[Dict[str, Any]] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    celery_task_id: Optional[str] = None
    error_message: Optional[str] = None
    priority: str = TaskPriority.NORMAL
    model_version_id: Optional[UUID] = None

    def start_processing(self) -> "EnhancedTask":
        """Mark task as processing and record start time."""
        self.status = TaskStatus.PROCESSING
        self.started_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        return self

    def complete(self, output_data: Dict[str, Any]) -> "EnhancedTask":
        """Mark task as completed with results."""
        self.status = TaskStatus.COMPLETED
        self.output_data = output_data
        self.completed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        return self

    def fail(self, error_message: str) -> "EnhancedTask":
        """Mark task as failed with error message."""
        self.status = TaskStatus.FAILED
        self.error_message = error_message
        self.completed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        return self

    def processing_time(self) -> Optional[float]:
        """Calculate processing time in seconds."""
        if not self.started_at or not self.completed_at:
            return None
        return (self.completed_at - self.started_at).total_seconds()

    def waiting_time(self) -> Optional[float]:
        """Calculate waiting time in seconds."""
        if not self.started_at:
            return None
        return (self.started_at - self.created_at).total_seconds()
