"""SQLAlchemy implementation of user repository."""
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ml_classifier.domain.entities.user import User
from ml_classifier.domain.repositories.user_repository import UserRepository
from ml_classifier.infrastructure.db.models import User as UserModel
from ml_classifier.infrastructure.db.repositories.base import SQLAlchemyRepository


class SQLAlchemyUserRepository(SQLAlchemyRepository[User, UserModel], UserRepository):
    """SQLAlchemy implementation of user repository."""

    def __init__(self, session: AsyncSession):
        """Initialize repository.

        Args:
            session: Database session
        """
        super().__init__(session, UserModel)

    def _db_to_entity(self, db_user: UserModel) -> User:
        """Convert database model to domain entity."""
        return User(
            id=db_user.id,
            email=db_user.email,
            hashed_password=db_user.hashed_password,
            full_name=db_user.full_name,
            is_active=db_user.is_active,
            is_admin=db_user.is_admin,
            balance=Decimal(str(db_user.balance)),
            created_at=db_user.created_at,
            updated_at=db_user.updated_at,
        )

    def _entity_to_db_values(self, entity: User) -> Dict:
        """Convert domain entity to database values dictionary."""
        return {
            "id": entity.id,
            "email": entity.email,
            "hashed_password": entity.hashed_password,
            "full_name": entity.full_name,
            "is_active": entity.is_active,
            "is_admin": entity.is_admin,
            "balance": float(entity.balance),
            "created_at": entity.created_at,
            "updated_at": entity.updated_at,
        }

    async def get_by_id(self, entity_id: UUID) -> Optional[User]:
        """Get user by ID."""
        result = await self.session.execute(
            select(UserModel).where(UserModel.id == entity_id)
        )
        db_user = result.scalars().first()
        if not db_user:
            return None
        return self._db_to_entity(db_user)

    async def create(self, entity: User) -> User:
        """Create new user."""
        db_user = UserModel(**self._entity_to_db_values(entity))
        self.session.add(db_user)
        await self.session.commit()
        await self.session.refresh(db_user)
        return self._db_to_entity(db_user)

    async def update(self, entity: User) -> User:
        """Update user."""
        values = self._entity_to_db_values(entity)
        values.pop("id", None)
        values.pop("created_at", None)
        values["updated_at"] = datetime.utcnow()

        stmt = (
            update(UserModel.__table__)
            .where(UserModel.id == entity.id)
            .values(**values)
        )
        await self.session.execute(stmt)
        await self.session.commit()

        updated = await self.get_by_id(entity.id)
        if not updated:
            raise ValueError(f"User with ID {entity.id} not found after update")
        return updated

    async def delete(self, entity_id: UUID) -> bool:
        """Delete user (soft delete)."""
        stmt = (
            update(UserModel.__table__)
            .where(UserModel.id == entity_id)
            .values(is_active=False, updated_at=datetime.utcnow())
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return bool(result.rowcount > 0)

    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        result = await self.session.execute(
            select(UserModel).where(UserModel.email == email)
        )
        db_user = result.scalars().first()
        if not db_user:
            return None
        return self._db_to_entity(db_user)

    async def update_balance(self, user_id: UUID, amount: Decimal) -> User:
        """Update user balance."""
        stmt = (
            update(UserModel.__table__)
            .where(UserModel.id == user_id)
            .values(
                balance=UserModel.balance + float(amount),
                updated_at=datetime.utcnow(),
            )
        )
        await self.session.execute(stmt)
        await self.session.commit()

        updated = await self.get_by_id(user_id)
        if not updated:
            raise ValueError(f"User with ID {user_id} not found after updating balance")
        return updated

    async def get_active_users(self) -> List[User]:
        """Get all active users."""
        result = await self.session.execute(
            select(UserModel).where(UserModel.is_active.is_(True))
        )
        db_users = result.scalars().all()
        return [self._db_to_entity(db_user) for db_user in db_users]

    async def get_admins(self) -> List[User]:
        """Get all admin users."""
        result = await self.session.execute(
            select(UserModel).where(
                and_(UserModel.is_admin.is_(True), UserModel.is_active.is_(True))
            )
        )
        db_users = result.scalars().all()
        return [self._db_to_entity(db_user) for db_user in db_users]
