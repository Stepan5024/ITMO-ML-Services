"""Profile-related data models."""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr


class ProfileBase(BaseModel):
    """Base model for profile data."""

    email: Optional[EmailStr] = None
    full_name: Optional[str] = None


class ProfileUpdate(ProfileBase):
    """Model for profile update data."""

    pass


class ProfileResponse(BaseModel):
    """Model for profile response data."""

    id: UUID
    email: EmailStr
    full_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    balance: float = 0.0
    is_active: bool = True
    is_admin: bool = False

    class Config:
        """Pydantic configuration."""

        orm_mode = True
