# src/ml_classifier/infrastructure/db/repositories/model_repository.py
"""SQLAlchemy implementation of model repository."""
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy import and_, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ml_classifier.domain.entities.model import Model
from ml_classifier.domain.repositories.model_repository import ModelRepository
from ml_classifier.infrastructure.db.models import Model as ModelModel
from ml_classifier.infrastructure.db.repositories.base import SQLAlchemyRepository


class SQLAlchemyModelRepository(
    SQLAlchemyRepository[Model, ModelModel], ModelRepository
):
    """SQLAlchemy implementation of model repository."""

    def __init__(self, session: AsyncSession):
        """Initialize repository.

        Args:
            session: Database session
        """
        super().__init__(session, ModelModel)

    def _db_to_entity(self, db_model: ModelModel) -> Model:
        """Convert database model to domain entity."""
        return Model(
            id=db_model.id,
            name=db_model.name,
            description=db_model.description,
            version=db_model.version,
            input_schema=db_model.input_schema or {},
            output_schema=db_model.output_schema or {},
            price_per_call=Decimal(str(db_model.price_per_request)),
            is_active=db_model.is_active,
            created_at=db_model.created_at,
            updated_at=db_model.updated_at,
        )

    def _entity_to_db_values(self, entity: Model) -> Dict:
        """Convert domain entity to database values dictionary."""
        return {
            "id": entity.id,
            "name": entity.name,
            "description": entity.description,
            "version": entity.version,
            "input_schema": entity.input_schema,
            "output_schema": entity.output_schema,
            "price_per_request": float(entity.price_per_call),
            "is_active": entity.is_active,
            "created_at": entity.created_at,
            "updated_at": entity.updated_at,
        }

    async def get_by_id(self, entity_id: UUID) -> Optional[Model]:
        """Get model by ID."""
        result = await self.session.execute(
            select(ModelModel).where(ModelModel.id == entity_id)
        )
        db_model = result.scalars().first()
        if not db_model:
            return None
        return self._db_to_entity(db_model)

    async def create(self, entity: Model) -> Model:
        """Create new model."""
        db_model = ModelModel(**self._entity_to_db_values(entity))
        self.session.add(db_model)
        await self.session.commit()
        await self.session.refresh(db_model)
        return self._db_to_entity(db_model)

    async def update(self, entity: Model) -> Model:
        """Update model."""
        values = self._entity_to_db_values(entity)
        values.pop("id", None)
        values.pop("created_at", None)
        values["updated_at"] = datetime.utcnow()

        stmt = (
            update(self.model_class.__table__)
            .where(self.model_class.id == entity.id)
            .values(**values)
        )
        await self.session.execute(stmt)
        await self.session.commit()

        result = await self.get_by_id(entity.id)
        if result is None:
            raise ValueError(f"Model with ID {entity.id} not found after update")
        return result

    async def delete(self, entity_id: UUID) -> bool:
        """Delete model (soft delete)."""
        stmt = (
            update(self.model_class.__table__)
            .where(self.model_class.id == entity_id)
            .values(is_active=False, updated_at=datetime.utcnow())
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return bool(result.rowcount > 0)

    async def get_active_models(self) -> List[Model]:
        """Get all active models."""
        return await self.get_all_active()

    async def get_by_name(self, name: str) -> Optional[Model]:
        """Get model by name."""
        result = await self.session.execute(
            select(ModelModel).where(ModelModel.name == name)
        )
        db_model = result.scalars().first()
        if not db_model:
            return None
        return self._db_to_entity(db_model)

    async def get_all_active(self) -> List[Model]:
        """Get all active models."""
        result = await self.session.execute(
            select(ModelModel).where(ModelModel.is_active.is_(True))
        )
        db_models = result.scalars().all()
        return [self._db_to_entity(db_model) for db_model in db_models]

    async def search_models(
        self, query: str, skip: int = 0, limit: int = 20
    ) -> List[Model]:
        """Search models by name or description."""
        search_pattern = f"%{query}%"
        result = await self.session.execute(
            select(ModelModel)
            .where(
                and_(
                    ModelModel.is_active.is_(True),
                    or_(
                        ModelModel.name.ilike(search_pattern),
                        ModelModel.description.ilike(search_pattern),
                    ),
                )
            )
            .order_by(ModelModel.name)
            .offset(skip)
            .limit(limit)
        )
        db_models = result.scalars().all()
        return [self._db_to_entity(db_model) for db_model in db_models]

    async def get_latest_version(self, model_name: str) -> Optional[Model]:
        """Get latest version of a model by name."""
        result = await self.session.execute(
            select(ModelModel)
            .where(
                and_(
                    ModelModel.name == model_name,
                    ModelModel.is_active.is_(True),
                )
            )
            .order_by(ModelModel.version.desc())
            .limit(1)
        )
        db_model = result.scalars().first()
        if not db_model:
            return None
        return self._db_to_entity(db_model)
