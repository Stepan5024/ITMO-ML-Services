"""Task monitoring API controller."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ml_classifier.infrastructure.db.database import get_db
from ml_classifier.infrastructure.db.repositories.task_repository import (
    SQLAlchemyTaskRepository,
)

from ml_classifier.domain.entities.user import User
from ml_classifier.infrastructure.web.auth_middleware import get_current_active_user
from ml_classifier.services.task_monitor_service import TaskMonitorService
from pydantic import BaseModel
from typing import Dict, Any, List, Optional

router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])


# Response models
class TaskStatus(BaseModel):
    """Response model for task status."""

    task_id: str
    status: str
    state: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    progress: Optional[float] = None


class TaskInfo(BaseModel):
    """Response model for task information."""

    id: str
    model_id: str
    status: str
    created_at: str
    completed_at: Optional[str] = None
    duration: Optional[float] = None
    output_summary: Optional[str] = None
    output_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


class TaskListResponse(BaseModel):
    """Response model for task list."""

    items: List[TaskInfo]
    total: int
    page: int
    size: int
    pages: int


@router.get("/{task_id}", response_model=TaskStatus)
async def get_task_status(
    task_id: str,
    current_user: User = Depends(get_current_active_user),
):
    """
    Get the status of a specific task.

    Args:
        task_id: The ID of the task to check
        current_user: The current authenticated user

    Returns:
        Task status information
    """
    task_monitor = TaskMonitorService()
    try:
        task_status = await task_monitor.get_task_status(task_id, current_user.id)
        return task_status
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.get("/", response_model=TaskListResponse)
async def get_user_tasks(
    status: Optional[str] = Query(None, description="Filter by task status"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Page size"),
    current_user: User = Depends(get_current_active_user),
    db_session: AsyncSession = Depends(get_db),
):
    """Получает список задач для текущего пользователя."""
    task_repository = SQLAlchemyTaskRepository(db_session)
    task_monitor = TaskMonitorService(task_repository)
    tasks, total = await task_monitor.get_user_tasks(
        user_id=current_user.id,
        status=status,
        page=page,
        size=size,
        is_admin=current_user.is_admin,
    )

    pages = (total + size - 1) // size if size > 0 else 0

    return {"items": tasks, "total": total, "page": page, "size": size, "pages": pages}


@router.post("/{task_id}/revoke", response_model=Dict[str, Any])
async def revoke_task(
    task_id: str,
    current_user: User = Depends(get_current_active_user),
):
    """
    Revoke (cancel) a running task.

    Args:
        task_id: The ID of the task to revoke
        current_user: The current authenticated user

    Returns:
        Result of the revocation operation
    """
    task_monitor = TaskMonitorService()
    try:
        result = await task_monitor.revoke_task(task_id, current_user.id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{task_id}/retry", response_model=Dict[str, Any])
async def retry_task(
    task_id: str,
    current_user: User = Depends(get_current_active_user),
):
    """
    Retry a failed task.

    Args:
        task_id: The ID of the failed task to retry
        current_user: The current authenticated user

    Returns:
        Information about the new task
    """
    task_monitor = TaskMonitorService()
    try:
        result = await task_monitor.retry_task(task_id, current_user.id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
