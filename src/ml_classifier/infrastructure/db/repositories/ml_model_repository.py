"""SQLAlchemy implementation of ML Model repository."""
from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from loguru import logger
from sqlalchemy import and_, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ml_classifier.domain.entities.ml_model import MLModel as MLModelEntity
from ml_classifier.domain.entities.ml_model import ModelType
from ml_classifier.domain.repositories.ml_model_repository import MLModelRepository
from ml_classifier.infrastructure.db.models import MLModel as MLModelDB
from ml_classifier.infrastructure.db.repositories.base import SQLAlchemyRepository


class SQLAlchemyMLModelRepository(
    SQLAlchemyRepository[MLModelEntity, MLModelDB], MLModelRepository
):
    """SQLAlchemy implementation of ML Model repository."""

    def __init__(self, session: AsyncSession):
        """
        Initialize repository.

        Args:
            session: Database session
        """
        super().__init__(session, MLModelDB)

    def _db_to_entity(self, db_model: MLModelDB) -> MLModelEntity:
        """
        Convert database model to domain entity.

        Args:
            db_model: Database model instance

        Returns:
            MLModelEntity: Domain entity
        """
        return MLModelEntity(
            id=db_model.id,
            name=db_model.name,
            description=db_model.description,
            model_type=db_model.model_type,
            algorithm=db_model.algorithm,
            input_schema=db_model.input_schema or {},
            output_schema=db_model.output_schema or {},
            is_active=db_model.is_active,
            price_per_call=db_model.price_per_call,
            created_at=db_model.created_at,
            updated_at=db_model.updated_at,
        )

    def _entity_to_db_values(self, entity: MLModelEntity) -> Dict:
        """
        Convert domain entity to database values dictionary.

        Args:
            entity: Domain entity

        Returns:
            Dict: Dictionary of database values
        """
        return {
            "id": entity.id,
            "name": entity.name,
            "description": entity.description,
            "model_type": entity.model_type,
            "algorithm": entity.algorithm,
            "input_schema": entity.input_schema,
            "output_schema": entity.output_schema,
            "is_active": entity.is_active,
            "price_per_call": float(entity.price_per_call),
            "created_at": entity.created_at,
            "updated_at": entity.updated_at,
        }

    async def get_by_id(self, entity_id: UUID) -> Optional[MLModelEntity]:
        """
        Get model by ID.

        Args:
            entity_id: Model ID

        Returns:
            Optional[MLModelEntity]: Found model or None
        """
        logger.info(f"Attempting to get model with ID: {entity_id}")
        result = await self.session.execute(
            select(MLModelDB).where(MLModelDB.id == entity_id)
        )
        db_model = result.scalars().first()
        if db_model is None:
            logger.warning(f"Model with ID {entity_id} not found in database")
            try:
                from ml_classifier.infrastructure.db.models import (
                    Model as RegularModelDB,
                )

                regular_stmt = select(RegularModelDB).where(
                    RegularModelDB.id == entity_id
                )
                regular_result = await self.session.execute(regular_stmt)
                regular_db_model = regular_result.scalars().first()

                if regular_db_model:
                    logger.warning(
                        f"Model with ID {entity_id} found in regular models table but not ML models table"
                    )
                else:
                    logger.warning(
                        f"Model with ID {entity_id} not found in regular models table either"
                    )
            except Exception as e:
                logger.error(f"Error checking regular models table: {str(e)}")
        else:
            logger.info(f"Model with ID {entity_id} found")
        return None if db_model is None else self._db_to_entity(db_model)

    async def create(self, entity: MLModelEntity) -> MLModelEntity:
        """
        Create new model.

        Args:
            entity: Model entity to create

        Returns:
            MLModelEntity: Created model
        """
        db_model = MLModelDB(**self._entity_to_db_values(entity))
        self.session.add(db_model)
        await self.session.commit()
        await self.session.refresh(db_model)
        return self._db_to_entity(db_model)

    async def update(self, entity: MLModelEntity) -> MLModelEntity:
        """
        Update model.

        Args:
            entity: Model entity with updated values

        Returns:
            MLModelEntity: Updated model
        """
        values = self._entity_to_db_values(entity)
        values.pop("id", None)
        values.pop("created_at", None)
        values["updated_at"] = datetime.utcnow()

        stmt = update(MLModelDB).where(MLModelDB.id == entity.id).values(**values)
        await self.session.execute(stmt)
        await self.session.commit()

        result = await self.get_by_id(entity.id)
        if result is None:
            raise ValueError(f"Model with ID {entity.id} not found after update")
        return result

    async def delete(self, entity_id: UUID) -> bool:
        """
        Delete model.

        Args:
            entity_id: Model ID

        Returns:
            bool: True if successful
        """
        stmt = (
            update(MLModelDB)
            .where(MLModelDB.id == entity_id)
            .values(is_active=False, updated_at=datetime.utcnow())
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return bool(result.rowcount > 0)

    async def get_by_name(self, name: str) -> Optional[MLModelEntity]:
        """
        Get model by name.

        Args:
            name: Model name

        Returns:
            Optional[MLModelEntity]: Found model or None
        """
        result = await self.session.execute(
            select(MLModelDB).where(MLModelDB.name == name)
        )
        db_model = result.scalars().first()
        return None if db_model is None else self._db_to_entity(db_model)

    async def get_active_models(self) -> List[MLModelEntity]:
        """
        Get all active models.

        Returns:
            List[MLModelEntity]: Active models
        """
        result = await self.session.execute(
            select(MLModelDB).where(MLModelDB.is_active.is_(True))
        )
        db_models = result.scalars().all()
        return [self._db_to_entity(m) for m in db_models]

    async def search_models(
        self,
        query: str,
        model_type: Optional[ModelType] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> List[MLModelEntity]:
        """
        Search models by name, description, or algorithm.

        Args:
            query: Search term
            model_type: Optional filter by model type
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List[MLModelEntity]: Matching models
        """
        search_term = f"%{query}%"

        # Build the search condition
        search_condition = or_(
            MLModelDB.name.ilike(search_term),
            MLModelDB.description.ilike(search_term)
            if MLModelDB.description is not None
            else False,
            MLModelDB.algorithm.ilike(search_term),
        )

        # Add model_type filter if provided
        if model_type:
            stmt = select(MLModelDB).where(
                and_(search_condition, MLModelDB.model_type == model_type)
            )
        else:
            stmt = select(MLModelDB).where(search_condition)

        # Add pagination
        stmt = stmt.order_by(MLModelDB.name).offset(skip).limit(limit)

        result = await self.session.execute(stmt)
        db_models = result.scalars().all()
        return [self._db_to_entity(m) for m in db_models]

    async def update_status(self, model_id: UUID, is_active: bool) -> MLModelEntity:
        """
        Update model active status.

        Args:
            model_id: Model ID
            is_active: New active status

        Returns:
            MLModelEntity: Updated model
        """
        stmt = (
            update(MLModelDB)
            .where(MLModelDB.id == model_id)
            .values(is_active=is_active, updated_at=datetime.utcnow())
        )
        await self.session.execute(stmt)
        await self.session.commit()

        result = await self.get_by_id(model_id)
        if result is None:
            raise ValueError(f"Model with ID {model_id} not found after status update")
        return result

    async def get_model_types(self) -> List[ModelType]:
        """
        Get all unique model types.

        Returns:
            List[ModelType]: List of model types
        """
        result = await self.session.execute(select(MLModelDB.model_type).distinct())
        return [row[0] for row in result.all()]
