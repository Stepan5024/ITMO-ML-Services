"""Authentication-related data models."""
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, validator

from ml_classifier.config.security import PASSWORD_MIN_LENGTH


class UserBase(BaseModel):
    """Base model for user data."""

    email: EmailStr
    full_name: Optional[str] = None


class UserCreate(UserBase):
    """Model for user creation."""

    password: str = Field(..., min_length=PASSWORD_MIN_LENGTH)

    @validator("password")
    def password_strength(cls, v):
        """Validate password meets complexity requirements."""
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class UserLogin(BaseModel):
    """Model for user login."""

    email: EmailStr
    password: str


class UserResponse(UserBase):
    """Model for user response data."""

    id: UUID
    balance: float = 0.0
    is_active: bool = True
    is_admin: bool = False

    class Config:
        """Pydantic configuration."""

        orm_mode = True


class TokenResponse(BaseModel):
    """Model for token response."""

    access_token: str
    token_type: str = "bearer"


class ChangePasswordRequest(BaseModel):
    """Model for password change request."""

    current_password: str
    new_password: str = Field(..., min_length=PASSWORD_MIN_LENGTH)

    @validator("new_password")
    def password_strength(cls, v):
        """Validate password meets complexity requirements."""
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v
