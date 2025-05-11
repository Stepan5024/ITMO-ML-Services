# src/ml_classifier/infrastructure/db/repositories/ml_model_version_repository.py
"""SQLAlchemy implementation of ML Model Version repository."""
from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy import and_, select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from ml_classifier.domain.entities.ml_model_version import (
    MLModelVersion as MLModelVersionEntity,
)
from ml_classifier.domain.entities.ml_model_version import ModelVersionStatus
from ml_classifier.infrastructure.db.models import MLModelVersion as MLModelVersionDB
from ml_classifier.domain.repositories.ml_model_version_repository import (
    MLModelVersionRepository,
)
from ml_classifier.infrastructure.db.repositories.base import SQLAlchemyRepository


class SQLAlchemyMLModelVersionRepository(
    SQLAlchemyRepository[MLModelVersionEntity, MLModelVersionDB],
    MLModelVersionRepository,
):
    """SQLAlchemy implementation of ML Model Version repository."""

    def __init__(self, session: AsyncSession):
        """
        Initialize repository.

        Args:
            session: Database session
        """
        super().__init__(session, MLModelVersionDB)

    def _db_to_entity(self, db_model: MLModelVersionDB) -> MLModelVersionEntity:
        """
        Convert database model to domain entity.

        Args:
            db_model: Database model instance

        Returns:
            MLModelVersionEntity: Domain entity
        """
        return MLModelVersionEntity(
            id=db_model.id,
            model_id=db_model.model_id,
            version=db_model.version,
            file_path=db_model.file_path,
            metrics=db_model.metrics or {},
            parameters=db_model.parameters or {},
            is_default=db_model.is_default,
            created_by=db_model.created_by,
            file_size=db_model.file_size,
            status=db_model.status,
            created_at=db_model.created_at,
            updated_at=db_model.updated_at,
        )

    async def get_latest_or_id(
        self, model_id: UUID, version_id: Optional[UUID] = None
    ) -> MLModelVersionEntity:
        """
        Get a model version by ID or the latest version if ID is not provided.

        Args:
            model_id: The ID of the model
            version_id: Optional specific version ID

        Returns:
            MLModelVersionEntity: Found model version

        Raises:
            ModelVersionNotFoundError: If no version is found
        """
        if version_id:
            # Get specific version by ID
            version = await self.get_by_id(version_id)
            if not version or version.model_id != model_id:
                raise ValueError(f"Version {version_id} not found for model {model_id}")
            return version
        else:
            # Get default version or latest if no default exists
            default_version = await self.get_default_version(model_id)
            if default_version:
                return default_version

            # If no default version exists, get latest by creation date
            result = await self.session.execute(
                select(MLModelVersionDB)
                .where(MLModelVersionDB.model_id == model_id)
                .order_by(MLModelVersionDB.created_at.desc())
                .limit(1)
            )
            version = result.scalars().first()
            if not version:
                raise ValueError(f"No versions found for model {model_id}")
            return self._db_to_entity(version)

    def _entity_to_db_values(self, entity: MLModelVersionEntity) -> Dict:
        """
        Convert domain entity to database values dictionary.

        Args:
            entity: Domain entity

        Returns:
            Dict: Dictionary of database values
        """
        return {
            "id": entity.id,
            "model_id": entity.model_id,
            "version": entity.version,
            "file_path": entity.file_path,
            "metrics": entity.metrics,
            "parameters": entity.parameters,
            "is_default": entity.is_default,
            "created_by": entity.created_by,
            "file_size": entity.file_size,
            "status": entity.status,
            "created_at": entity.created_at,
            "updated_at": entity.updated_at,
        }

    async def get_by_id(self, entity_id: UUID) -> Optional[MLModelVersionEntity]:
        """
        Get version by ID.

        Args:
            entity_id: Version ID

        Returns:
            Optional[MLModelVersionEntity]: Found version or None
        """
        result = await self.session.execute(
            select(MLModelVersionDB).where(MLModelVersionDB.id == entity_id)
        )
        db_model = result.scalars().first()
        return None if db_model is None else self._db_to_entity(db_model)

    async def create(self, entity: MLModelVersionEntity) -> MLModelVersionEntity:
        """
        Create new model version.

        Args:
            entity: Version entity to create

        Returns:
            MLModelVersionEntity: Created version
        """
        db_model = MLModelVersionDB(**self._entity_to_db_values(entity))
        self.session.add(db_model)
        await self.session.commit()
        await self.session.refresh(db_model)
        return self._db_to_entity(db_model)

    async def update(self, entity: MLModelVersionEntity) -> MLModelVersionEntity:
        """
        Update model version.

        Args:
            entity: Version entity with updated values

        Returns:
            MLModelVersionEntity: Updated version
        """
        values = self._entity_to_db_values(entity)
        values.pop("id", None)
        values.pop("created_at", None)
        values.pop("created_by", None)  # Don't update creator
        values["updated_at"] = datetime.utcnow()

        stmt = (
            update(MLModelVersionDB)
            .where(MLModelVersionDB.id == entity.id)
            .values(**values)
        )
        await self.session.execute(stmt)
        await self.session.commit()

        result = await self.get_by_id(entity.id)
        if result is None:
            raise ValueError(
                f"Model version with ID {entity.id} not found after update"
            )
        return result

    async def delete(self, entity_id: UUID) -> bool:
        """
        Delete model version.

        Args:
            entity_id: Version ID

        Returns:
            bool: True if successful
        """
        stmt = delete(MLModelVersionDB).where(MLModelVersionDB.id == entity_id)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return bool(result.rowcount > 0)

    async def get_by_model_id(self, model_id: UUID) -> List[MLModelVersionEntity]:
        """
        Get all versions of a model.

        Args:
            model_id: Model ID

        Returns:
            List[MLModelVersionEntity]: Model versions
        """
        result = await self.session.execute(
            select(MLModelVersionDB)
            .where(MLModelVersionDB.model_id == model_id)
            .order_by(MLModelVersionDB.created_at.desc())
        )
        db_models = result.scalars().all()
        return [self._db_to_entity(m) for m in db_models]

    async def get_default_version(
        self, model_id: UUID
    ) -> Optional[MLModelVersionEntity]:
        """
        Get default version of a model.

        Args:
            model_id: Model ID

        Returns:
            Optional[MLModelVersionEntity]: Default version or None
        """
        result = await self.session.execute(
            select(MLModelVersionDB).where(
                and_(
                    MLModelVersionDB.model_id == model_id,
                    MLModelVersionDB.is_default.is_(True),
                )
            )
        )
        db_model = result.scalars().first()
        return None if db_model is None else self._db_to_entity(db_model)

    async def set_default_version(self, version_id: UUID) -> MLModelVersionEntity:
        """
        Set a version as default for its model.

        Args:
            version_id: Version ID

        Returns:
            MLModelVersionEntity: Updated version
        """
        stmt = (
            update(MLModelVersionDB)
            .where(MLModelVersionDB.id == version_id)
            .values(is_default=True, updated_at=datetime.utcnow())
        )
        await self.session.execute(stmt)
        await self.session.commit()

        result = await self.get_by_id(version_id)
        if result is None:
            raise ValueError(
                f"Model version with ID {version_id} not found after setting as default"
            )
        return result

    async def unset_default_versions(self, model_id: UUID) -> None:
        """
        Unset default flag for all versions of a model.

        Args:
            model_id: Model ID
        """
        stmt = (
            update(MLModelVersionDB)
            .where(
                and_(
                    MLModelVersionDB.model_id == model_id,
                    MLModelVersionDB.is_default.is_(True),
                )
            )
            .values(is_default=False, updated_at=datetime.utcnow())
        )
        await self.session.execute(stmt)
        await self.session.commit()

    async def get_by_model_id_and_version(
        self, model_id: UUID, version: str
    ) -> Optional[MLModelVersionEntity]:
        """
        Get specific version of a model.

        Args:
            model_id: Model ID
            version: Version string

        Returns:
            Optional[MLModelVersionEntity]: Found version or None
        """
        result = await self.session.execute(
            select(MLModelVersionDB).where(
                and_(
                    MLModelVersionDB.model_id == model_id,
                    MLModelVersionDB.version == version,
                )
            )
        )
        db_model = result.scalars().first()
        return None if db_model is None else self._db_to_entity(db_model)

    async def update_status(
        self, version_id: UUID, status: ModelVersionStatus
    ) -> MLModelVersionEntity:
        """
        Update version status.

        Args:
            version_id: Version ID
            status: New status

        Returns:
            MLModelVersionEntity: Updated version
        """
        stmt = (
            update(MLModelVersionDB)
            .where(MLModelVersionDB.id == version_id)
            .values(status=status, updated_at=datetime.utcnow())
        )
        await self.session.execute(stmt)
        await self.session.commit()

        result = await self.get_by_id(version_id)
        if result is None:
            raise ValueError(
                f"Model version with ID {version_id} not found after status update"
            )
        return result
