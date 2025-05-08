# src/ml_classifier/infrastructure/db/repositories/task_repository.py
"""SQLAlchemy implementation of task repository."""
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ml_classifier.domain.entities import Task
from ml_classifier.domain.entities.enums import TaskStatus
from ml_classifier.domain.repositories.task_repository import TaskRepository
from ml_classifier.infrastructure.db.models import Task as TaskModel
from ml_classifier.infrastructure.db.repositories.base import SQLAlchemyRepository


class SQLAlchemyTaskRepository(
    SQLAlchemyRepository[Task, TaskModel],
    TaskRepository,
):
    """SQLAlchemy implementation of TaskRepository."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, TaskModel)

    def _db_to_entity(self, db_task: TaskModel) -> Task:
        return Task(
            id=db_task.id,
            user_id=db_task.user_id,
            model_id=db_task.model_id,
            input_data={"text": db_task.input_text},
            status=db_task.status,
            output_data=db_task.result,
            completed_at=db_task.completed_at,
            error_message=db_task.error_message,
            created_at=db_task.created_at,
            updated_at=db_task.updated_at,
        )

    def _entity_to_db_values(self, entity: Task) -> Dict[str, Any]:
        input_text = entity.input_data.get("text", "") if entity.input_data else ""
        return {
            "id": entity.id,
            "user_id": entity.user_id,
            "model_id": entity.model_id,
            "input_text": input_text,
            "result": entity.output_data,
            "status": entity.status,
            "error_message": entity.error_message,
            "completed_at": entity.completed_at,
            "created_at": entity.created_at,
            "updated_at": entity.updated_at,
        }

    async def get_by_id(self, entity_id: UUID) -> Optional[Task]:
        result = await self.session.execute(
            select(TaskModel).where(TaskModel.id == entity_id)
        )
        db_task = result.scalars().first()
        return None if db_task is None else self._db_to_entity(db_task)

    async def create(self, entity: Task) -> Task:
        db_task = TaskModel(**self._entity_to_db_values(entity))
        self.session.add(db_task)
        await self.session.commit()
        await self.session.refresh(db_task)
        return self._db_to_entity(db_task)

    async def update(self, entity: Task) -> Task:
        values = self._entity_to_db_values(entity)
        values.pop("id", None)
        values.pop("created_at", None)
        values["updated_at"] = datetime.utcnow()

        stmt = (
            update(TaskModel)  # type: ignore[arg-type]
            .where(TaskModel.id == entity.id)
            .values(**values)
        )
        await self.session.execute(stmt)
        await self.session.commit()

        task = await self.get_by_id(entity.id)
        assert task is not None, f"Task {entity.id} vanished after update"
        return task

    async def delete(self, entity_id: UUID) -> bool:
        stmt = delete(TaskModel).where(  # type: ignore[arg-type]
            TaskModel.id == entity_id
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return bool(result.rowcount and result.rowcount > 0)

    async def get_by_user_id(self, user_id: UUID) -> List[Task]:
        result = await self.session.execute(
            select(TaskModel).where(TaskModel.user_id == user_id)
        )
        return [self._db_to_entity(t) for t in result.scalars().all()]

    async def update_status(
        self,
        task_id: UUID,
        status: str,  # match base signature
        output_data: Optional[Dict[str, Any]] = None,
    ) -> Task:
        try:
            enum_status = TaskStatus(status)
        except ValueError:
            raise ValueError(f"Unknown TaskStatus: {status}")

        values: Dict[str, Any] = {
            "status": enum_status,
            "updated_at": datetime.utcnow(),
        }
        if enum_status == TaskStatus.COMPLETED:
            values["completed_at"] = datetime.utcnow()
        if output_data is not None:
            values["result"] = output_data

        stmt = (
            update(TaskModel)  # type: ignore[arg-type]
            .where(TaskModel.id == task_id)
            .values(**values)
        )
        await self.session.execute(stmt)
        await self.session.commit()

        task = await self.get_by_id(task_id)
        if task is None:
            raise ValueError(f"Task with ID {task_id} not found after status update")
        return task

    async def get_pending_tasks(self, limit: int = 10) -> List[Task]:
        result = await self.session.execute(
            select(TaskModel)
            .where(TaskModel.status == TaskStatus.PENDING)
            .order_by(TaskModel.created_at)
            .limit(limit)
        )
        return [self._db_to_entity(t) for t in result.scalars().all()]

    async def get_by_status(self, status: TaskStatus) -> List[Task]:
        result = await self.session.execute(
            select(TaskModel).where(TaskModel.status == status)
        )
        return [self._db_to_entity(t) for t in result.scalars().all()]

    async def get_user_tasks_count(self, user_id: UUID) -> Dict[TaskStatus, int]:
        result = await self.session.execute(
            select([TaskModel.status, func.count(TaskModel.id)])
            .where(TaskModel.user_id == user_id)
            .group_by(TaskModel.status)
        )
        counts = {row[0]: row[1] for row in result.all()}
        return {
            status: counts.get(status, 0) for status in TaskStatus.__members__.values()
        }

    async def mark_as_completed(self, task_id: UUID, result: Dict[str, Any]) -> Task:
        task = await self.get_by_id(task_id)
        if not task:
            raise ValueError(f"Task with ID {task_id} not found")
        task.complete(result)
        return await self.update(task)

    async def mark_as_failed(self, task_id: UUID, error_message: str) -> Task:
        task = await self.get_by_id(task_id)
        if not task:
            raise ValueError(f"Task with ID {task_id} not found")
        task.fail(error_message)
        return await self.update(task)
