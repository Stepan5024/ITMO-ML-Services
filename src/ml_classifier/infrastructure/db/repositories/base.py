"""Base SQLAlchemy repository implementation."""

from abc import ABC, abstractmethod
from typing import Any, Generic, List, Optional, Protocol, Type, TypeVar, cast
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ml_classifier.domain.entities.base import Entity
from ml_classifier.domain.repositories.base import Repository


class HasID(Protocol):
    id: UUID


T = TypeVar("T", bound=Entity)
M = TypeVar("M", bound=HasID)


class SQLAlchemyRepository(Repository[T], Generic[T, M], ABC):
    """Base SQLAlchemy repository implementation."""

    def __init__(self, session: AsyncSession, model_class: Type[M]):
        """
        Args:
            session: Database session
            model_class: SQLAlchemy model class
        """
        self.session = session
        self.model_class = model_class

    @abstractmethod
    async def get_by_id(self, entity_id: UUID) -> Optional[T]:
        """Retrieve entity by ID."""
        pass

    @abstractmethod
    async def create(self, entity: T) -> T:
        """Create a new entity."""
        pass

    @abstractmethod
    async def update(self, entity: T) -> T:
        """Update an existing entity."""
        pass

    @abstractmethod
    async def delete(self, entity_id: UUID) -> bool:
        """Delete entity by ID."""
        pass

    async def count(self) -> int:
        """Get total number of entities."""
        result = await self.session.execute(
            select(func.count(cast(Any, self.model_class).id))
        )
        return int(result.scalar_one())

    async def exists(self, entity_id: UUID) -> bool:
        """Check if entity exists by ID."""
        result = await self.session.execute(
            select(func.count(cast(Any, self.model_class).id)).where(
                cast(Any, self.model_class).id == entity_id
            )
        )
        return int(result.scalar_one()) > 0

    async def list(self, skip: int = 0, limit: int = 100) -> List[T]:
        """Get list of entities with pagination."""
        stmt = select(cast(Any, self.model_class))
        stmt = stmt.offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        db_entities = result.scalars().all()
        return [self._db_to_entity(db_model) for db_model in db_entities]

    @abstractmethod
    def _db_to_entity(self, db_model: M) -> T:
        """Convert database model to domain entity."""
        pass

    @abstractmethod
    def _entity_to_db_values(self, entity: T) -> dict:
        """Convert domain entity to database values dictionary."""
        pass
