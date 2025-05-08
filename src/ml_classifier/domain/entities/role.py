"""Role entity for user permissions."""
from enum import Enum

from ml_classifier.domain.entities.base import Entity


class RoleType(str, Enum):
    """Available user roles in the system."""

    USER = "USER"
    ADMIN = "ADMIN"


class Permission(str, Enum):
    """Available permissions in the system."""

    READ_USER = "read:user"
    WRITE_USER = "write:user"
    DELETE_USER = "delete:user"

    READ_MODEL = "read:model"
    WRITE_MODEL = "write:model"

    READ_TASK = "read:task"
    WRITE_TASK = "write:task"

    READ_TRANSACTION = "read:transaction"
    WRITE_TRANSACTION = "write:transaction"


class Role(Entity):
    """User role entity."""

    name: RoleType
    permissions: list[Permission]
