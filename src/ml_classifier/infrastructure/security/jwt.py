from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from uuid import UUID

from jose import jwt

from ml_classifier.config.security import (
    JWT_ALGORITHM,
    JWT_SECRET_KEY,
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES,
)


def create_access_token(
    subject: UUID,
    email: str,
    is_admin: bool = False,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create a JWT access token.

    Args:
        subject: User ID to encode in the token
        email: User email
        is_admin: Whether the user is an admin
        expires_delta: Optional override for token expiration

    Returns:
        str: Encoded JWT token
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode = {
        "sub": str(subject),
        "email": email,
        "is_admin": is_admin,
        "exp": expire,
        "iat": datetime.utcnow(),
    }

    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT token."""
    return jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
