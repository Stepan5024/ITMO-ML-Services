# src/ml_classifier/services/user_use_cases.py
"""User-related business logic and use cases."""
from typing import Optional, Tuple
from uuid import UUID

from fastapi import Depends
from passlib.context import CryptContext

from ml_classifier.domain.entities.user import User
from ml_classifier.domain.repositories.user_repository import UserRepository
from ml_classifier.infrastructure.db.repositories.user_repository import (
    SQLAlchemyUserRepository,
)
from ml_classifier.infrastructure.db.database import get_db
from ml_classifier.infrastructure.security.password import (
    validate_password_strength,
    validate_email_format,
)

# Password context for direct hashing when needed
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserUseCase:
    """Business logic for user operations."""

    def __init__(self, user_repository: UserRepository):
        """Initialize with user repository."""
        self.user_repository = user_repository

    async def register_user(
        self,
        email: str,
        password: str,
        full_name: Optional[str] = None,
        is_admin: bool = False,
    ) -> Tuple[bool, str, Optional[User]]:
        """
        Register a new user with validation.

        Args:
            email: User's email address
            password: Plain-text password
            full_name: Optional full name
            is_admin: Whether user has admin privileges

        Returns:
            Tuple[bool, str, Optional[User]]: (success, message, created_user)
        """
        # Validate email format
        if not validate_email_format(email):
            return False, "Invalid email format.", None

        # Validate password strength
        valid_password, error_msg = validate_password_strength(password)
        if not valid_password:
            return False, error_msg, None

        # Check if email is already registered
        existing_user = await self.user_repository.get_by_email(email)
        if existing_user:
            return False, f"Email {email} is already registered.", None

        # Create user with hashed password
        user = User.create(
            email=email,
            password=password,
            full_name=full_name,
            is_admin=is_admin,
        )

        created_user = await self.user_repository.create(user)
        return True, "User registered successfully.", created_user

    async def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """
        Authenticate user with email and password.

        Args:
            email: User's email
            password: Plain-text password

        Returns:
            Optional[User]: Authenticated user or None if authentication fails
        """
        user = await self.user_repository.get_by_email(email)
        if not user:
            return None

        if not user.verify_password(password):
            return None

        return user

    async def get_user_by_id(self, user_id: UUID) -> Optional[User]:
        """Get user by ID."""
        return await self.user_repository.get_by_id(user_id)

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        return await self.user_repository.get_by_email(email)

    async def update_user(
        self, user_id: UUID, full_name: Optional[str] = None
    ) -> Tuple[bool, str, Optional[User]]:
        """
        Update user information.

        Args:
            user_id: User ID
            full_name: New full name

        Returns:
            Tuple[bool, str, Optional[User]]: (success, message, updated_user)
        """
        user = await self.get_user_by_id(user_id)
        if not user:
            return False, f"User with ID {user_id} not found.", None

        if full_name is not None:
            # Create a new user instance with updated values
            # We need to create a new instance because User is immutable (frozen=True)
            user = User(
                id=user.id,
                email=user.email,
                hashed_password=user.hashed_password,
                full_name=full_name,
                is_active=user.is_active,
                is_admin=user.is_admin,
                balance=user.balance,
                created_at=user.created_at,
                updated_at=user.updated_at,
            )

        try:
            updated_user = await self.user_repository.update(user)
            return True, "User updated successfully.", updated_user
        except Exception as e:
            return False, f"Failed to update user: {str(e)}", None

    async def change_password(
        self, user_id: UUID, current_password: str, new_password: str
    ) -> Tuple[bool, str]:
        """
        Change user's password with validation.

        Args:
            user_id: User ID
            current_password: Current password for verification
            new_password: New password

        Returns:
            Tuple[bool, str]: (success, message)
        """
        user = await self.get_user_by_id(user_id)
        if not user:
            return False, f"User with ID {user_id} not found."

        # Verify current password
        if not user.verify_password(current_password):
            return False, "Current password is incorrect."

        # Validate new password strength
        valid_password, error_msg = validate_password_strength(new_password)
        if not valid_password:
            return False, error_msg

        # Hash and update password
        hashed_password = pwd_context.hash(new_password)

        # Create a new user instance with updated password
        updated_user = User(
            id=user.id,
            email=user.email,
            hashed_password=hashed_password,
            full_name=user.full_name,
            is_active=user.is_active,
            is_admin=user.is_admin,
            balance=user.balance,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )

        try:
            await self.user_repository.update(updated_user)
            return True, "Password updated successfully."
        except Exception as e:
            return False, f"Failed to update password: {str(e)}"


async def get_user_repository(session=Depends(get_db)) -> UserRepository:
    """Dependency to get UserRepository implementation."""
    return SQLAlchemyUserRepository(session)


def get_user_use_case(
    user_repo: UserRepository = Depends(get_user_repository),
) -> UserUseCase:
    """Dependency to get UserUseCase instance."""
    return UserUseCase(user_repo)
