# migrations/versions/20250513_add_description_to_transactions.py
"""Add description to transactions

Revision ID: 202505130000
Revises: 202505060000
Create Date: 2025-05-13 00:00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "202505130000"
down_revision = "20250510_add_ml_models"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add description column to transactions table
    op.add_column("transactions", sa.Column("description", sa.String(), nullable=True))


def downgrade() -> None:
    # Remove description column
    op.drop_column("transactions", "description")
