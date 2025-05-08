# src/ml_classifier/infrastructure/web/auth_middleware.py
"""Authentication middleware and dependencies."""
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError

from ml_classifier.domain.entities.user import User
from ml_classifier.infrastructure.security.jwt import decode_token
from ml_classifier.services.user_use_cases import UserUseCase, get_user_use_case

# OAuth2 scheme for token extraction
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    user_use_case: UserUseCase = Depends(get_user_use_case),
) -> User:
    """
    Extract and validate the current user from JWT token.

    Args:
        token: JWT token from Authorization header
        user_use_case: User use case dependency

    Returns:
        User: Current authenticated user

    Raises:
        HTTPException: If token is invalid or user not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_token(token)
        user_id_str = payload.get("sub")
        if user_id_str is None:
            raise credentials_exception

        user_id = UUID(user_id_str)
    except (JWTError, ValueError):
        raise credentials_exception

    user = await user_use_case.get_user_by_id(user_id)
    if user is None:
        raise credentials_exception

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Verify that the current user is active.

    Args:
        current_user: Current authenticated user

    Returns:
        User: Current active user

    Raises:
        HTTPException: If user is inactive
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )
    return current_user


async def get_current_admin_user(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """
    Verify that the current user has admin privileges.

    Args:
        current_user: Current active user

    Returns:
        User: Current admin user

    Raises:
        HTTPException: If user is not an admin
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )
    return current_user
