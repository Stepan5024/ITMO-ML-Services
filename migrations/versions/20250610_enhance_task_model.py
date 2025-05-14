"""Add additional fields to Task model

Revision ID: enhance_task_model
Revises: 20250515_error_message
Create Date: 2025-06-10 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "enhance_task_model"
down_revision: Union[str, None] = "20250515_error_message"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add celery_task_id column
    op.add_column("tasks", sa.Column("celery_task_id", sa.String(255), nullable=True))

    # Add started_at column
    op.add_column("tasks", sa.Column("started_at", sa.DateTime(), nullable=True))

    # Add priority column with default 'normal'
    op.add_column(
        "tasks",
        sa.Column("priority", sa.String(10), nullable=False, server_default="normal"),
    )

    # Add model_version_id column
    op.add_column(
        "tasks", sa.Column("model_version_id", UUID(as_uuid=True), nullable=True)
    )

    # Add a foreign key constraint for model_version_id
    op.create_foreign_key(
        "fk_tasks_model_version",
        "tasks",
        "ml_model_versions",
        ["model_version_id"],
        ["id"],
    )

    # Create index for celery_task_id
    op.create_index("idx_tasks_celery_task_id", "tasks", ["celery_task_id"])

    # Create index for model_version_id
    op.create_index("idx_tasks_model_version_id", "tasks", ["model_version_id"])

    # Create compound index for user_id and priority
    op.create_index("idx_tasks_user_priority", "tasks", ["user_id", "priority"])


def downgrade() -> None:
    # Drop indexes
    op.drop_index("idx_tasks_user_priority")
    op.drop_index("idx_tasks_model_version_id")
    op.drop_index("idx_tasks_celery_task_id")

    # Drop foreign key constraint
    op.drop_constraint("fk_tasks_model_version", "tasks", type_="foreignkey")

    # Drop added columns
    op.drop_column("tasks", "model_version_id")
    op.drop_column("tasks", "priority")
    op.drop_column("tasks", "started_at")
    op.drop_column("tasks", "celery_task_id")
