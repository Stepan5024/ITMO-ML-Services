"""Admin user management use cases."""
import logging
from datetime import datetime
from typing import List, Optional, Tuple
from uuid import UUID

from fastapi import Depends

from ml_classifier.domain.entities.user import User
from ml_classifier.domain.repositories.user_repository import UserRepository
from ml_classifier.infrastructure.db.database import get_db
from ml_classifier.infrastructure.db.repositories.user_repository import (
    SQLAlchemyUserRepository,
)
from ml_classifier.models.admin import AdminUserFilter

logger = logging.getLogger(__name__)


class AdminUserUseCase:
    """Use case for admin user management operations."""

    def __init__(self, user_repository: UserRepository):
        """Initialize with user repository."""
        self.user_repository = user_repository

    async def list_users(self, filters: AdminUserFilter) -> Tuple[List[User], int]:
        """
        Get a list of users with filtering and pagination.

        Args:
            filters: Filter criteria

        Returns:
            Tuple[List[User], int]: List of users and total count
        """
        offset = (filters.page - 1) * filters.size

        all_users = await self.user_repository.list(skip=offset, limit=filters.size)

        filtered_users = []
        for user in all_users:
            if filters.search:
                search_term = filters.search.lower()
                if not (
                    (user.email and search_term in user.email.lower())
                    or (user.full_name and search_term in user.full_name.lower())
                ):
                    continue

            if filters.is_active is not None and user.is_active != filters.is_active:
                continue

            if filters.is_admin is not None and user.is_admin != filters.is_admin:
                continue

            filtered_users.append(user)

        filtered_count = len(filtered_users)

        return filtered_users, filtered_count

    async def get_user(self, user_id: UUID) -> Optional[User]:
        """
        Get a user by ID.

        Args:
            user_id: User ID

        Returns:
            Optional[User]: User if found
        """
        return await self.user_repository.get_by_id(user_id)

    async def update_user_status(
        self, user_id: UUID, is_active: bool
    ) -> Tuple[bool, str, Optional[User]]:
        """
        Update a user's active status.

        Args:
            user_id: User ID
            is_active: New active status

        Returns:
            Tuple[bool, str, Optional[User]]: Success, message, updated user
        """
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            return False, f"User with ID {user_id} not found", None

        updated_user = User(
            id=user.id,
            email=user.email,
            hashed_password=user.hashed_password,
            full_name=user.full_name,
            balance=user.balance,
            is_active=is_active,
            is_admin=user.is_admin,
            created_at=user.created_at,
            updated_at=datetime.utcnow(),
        )

        try:
            result = await self.user_repository.update(updated_user)
            status_str = "activated" if is_active else "deactivated"
            logger.info(f"User {user_id} has been {status_str}")
            return True, f"User has been {status_str}", result
        except Exception as e:
            logger.error(f"Error updating user status: {e}")
            return False, f"Error updating user status: {str(e)}", None

    async def set_admin_status(
        self, user_id: UUID, is_admin: bool
    ) -> Tuple[bool, str, Optional[User]]:
        """
        Set a user's admin status.

        Args:
            user_id: User ID
            is_admin: New admin status

        Returns:
            Tuple[bool, str, Optional[User]]: Success, message, updated user
        """
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            return False, f"User with ID {user_id} not found", None

        updated_user = User(
            id=user.id,
            email=user.email,
            hashed_password=user.hashed_password,
            full_name=user.full_name,
            balance=user.balance,
            is_active=user.is_active,
            is_admin=is_admin,
            created_at=user.created_at,
            updated_at=datetime.utcnow(),
        )

        try:
            result = await self.user_repository.update(updated_user)
            status_str = (
                "granted admin privileges" if is_admin else "revoked admin privileges"
            )
            logger.info(f"User {user_id} has been {status_str}")
            return True, f"User has been {status_str}", result
        except Exception as e:
            logger.error(f"Error updating admin status: {e}")
            return False, f"Error updating admin status: {str(e)}", None


async def get_admin_user_repository(session=Depends(get_db)) -> UserRepository:
    """Dependency to get UserRepository implementation."""
    return SQLAlchemyUserRepository(session)


def get_admin_user_use_case(
    user_repo: UserRepository = Depends(get_admin_user_repository),
) -> AdminUserUseCase:
    """Dependency to get AdminUserUseCase instance."""
    return AdminUserUseCase(user_repo)
