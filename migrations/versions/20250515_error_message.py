"""add error_message to tasks

Revision ID: 20250515_error_message
Revises: 202505130000
Create Date: 2025-05-15 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20250515_error_message"
down_revision: Union[str, None] = "202505130000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Добавляем колонку error_message к таблице tasks, если она отсутствует
    op.add_column("tasks", sa.Column("error_message", sa.Text(), nullable=True))


def downgrade() -> None:
    # Удаляем колонку при откате миграции
    op.drop_column("tasks", "error_message")
