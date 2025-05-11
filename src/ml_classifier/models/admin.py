"""Admin-related data models."""
from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class AdminUserFilter(BaseModel):
    """Filter model for admin user listing."""

    search: Optional[str] = None
    is_active: Optional[bool] = None
    is_admin: Optional[bool] = None
    page: int = 1
    size: int = 10


class AdminUserResponse(BaseModel):
    """Response model for admin user operations."""

    id: UUID
    email: EmailStr
    full_name: Optional[str] = None
    is_active: bool
    is_admin: bool
    balance: float
    created_at: datetime
    updated_at: datetime


class AdminUserListResponse(BaseModel):
    """Response model for admin user listing."""

    items: List[AdminUserResponse]
    total: int
    page: int
    size: int
    pages: int


class UserStatusUpdate(BaseModel):
    """Model for updating user status."""

    is_admin: bool


class RoleOperation(str, Enum):
    """Role operations for role assignment."""

    ADD = "add"
    REMOVE = "remove"
    SET = "set"


class RoleAssignment(BaseModel):
    """Model for role assignment operations."""

    roles: List[str] = Field(..., min_items=1)
    operation: RoleOperation = RoleOperation.SET


class UserBulkActionRequest(BaseModel):
    """Request model for bulk user actions."""

    user_ids: List[UUID] = Field(..., min_items=1)


class AdminActionLog(BaseModel):
    """Model for admin action logging."""

    admin_id: UUID
    action: str
    target_id: Optional[UUID] = None
    target_type: str
    details: Optional[dict] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
