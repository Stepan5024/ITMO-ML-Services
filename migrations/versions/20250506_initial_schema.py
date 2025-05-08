# migrations/versions/202310271200_initial_schema.py
"""initial schema

Revision ID: 202310271200
Revises:
Create Date: 2023-10-27 12:00:00

"""
import uuid
from datetime import datetime

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ENUM, JSONB, UUID

# revision identifiers, used by Alembic.
revision = "202310271200"
down_revision = None
branch_labels = None
depends_on = None

# Define all ENUM types
task_status = ENUM(
    "pending",
    "processing",
    "completed",
    "failed",
    name="task_status",
    create_type=False,
)

transaction_type = ENUM(
    "deposit", "withdraw", "task_payment", name="transaction_type", create_type=False
)

transaction_status = ENUM(
    "pending", "completed", "failed", name="transaction_status", create_type=False
)


def upgrade() -> None:
    connection = op.get_bind()

    task_status.create(connection, checkfirst=True)
    transaction_type.create(connection, checkfirst=True)
    transaction_status.create(connection, checkfirst=True)

    # Create users table
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("hashed_password", sa.String(), nullable=False),
        sa.Column("full_name", sa.String()),
        sa.Column("balance", sa.Numeric(10, 2), nullable=False, default=0.0),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, default=datetime.utcnow),
        sa.Column("updated_at", sa.DateTime(), nullable=False, default=datetime.utcnow),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_email", "users", ["email"])

    # Create models table
    op.create_table(
        "models",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("version", sa.String(), nullable=False),
        sa.Column("price_per_request", sa.Numeric(10, 2), nullable=False, default=0.0),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, default=datetime.utcnow),
        sa.Column("updated_at", sa.DateTime(), nullable=False, default=datetime.utcnow),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_models_name", "models", ["name"])

    # Create tasks table using the pre-defined ENUM
    op.create_table(
        "tasks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column(
            "user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False
        ),
        sa.Column(
            "model_id", UUID(as_uuid=True), sa.ForeignKey("models.id"), nullable=False
        ),
        sa.Column("input_text", sa.Text(), nullable=False),
        sa.Column("result", JSONB),
        sa.Column("status", task_status, default="pending", nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, default=datetime.utcnow),
        sa.Column("updated_at", sa.DateTime(), nullable=False, default=datetime.utcnow),
        sa.Column("completed_at", sa.DateTime()),
    )
    op.create_index("ix_tasks_user_id", "tasks", ["user_id"])
    op.create_index("ix_tasks_model_id", "tasks", ["model_id"])
    op.create_index("ix_tasks_status", "tasks", ["status"])
    op.create_index("ix_tasks_created_at", "tasks", ["created_at"])

    # Create transactions table using pre-defined ENUMs
    op.create_table(
        "transactions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column(
            "user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False
        ),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("type", transaction_type, nullable=False),
        sa.Column(
            "reference_id", UUID(as_uuid=True), sa.ForeignKey("tasks.id"), nullable=True
        ),
        sa.Column("status", transaction_status, default="pending", nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, default=datetime.utcnow),
        sa.Column("updated_at", sa.DateTime(), nullable=False, default=datetime.utcnow),
    )
    op.create_index("ix_transactions_user_id", "transactions", ["user_id"])
    op.create_index("ix_transactions_type", "transactions", ["type"])
    op.create_index("ix_transactions_created_at", "transactions", ["created_at"])


def downgrade() -> None:
    op.drop_table("transactions")
    op.drop_table("tasks")
    op.drop_table("models")
    op.drop_table("users")
    # Drop enums in reverse order
    connection = op.get_bind()
    transaction_status.drop(connection, checkfirst=True)
    transaction_type.drop(connection, checkfirst=True)
    task_status.drop(connection, checkfirst=True)
