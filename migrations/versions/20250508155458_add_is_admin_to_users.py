"""add_is_admin_to_users


Revises: 202310271200
Create Date: $(date -u +"%Y-%m-%d %H:%M:%S")

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "202310271201"
down_revision = "202310271200"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add is_admin column with default value False
    op.add_column(
        "users",
        sa.Column(
            "is_admin", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
    )


def downgrade() -> None:
    # Remove is_admin column
    op.drop_column("users", "is_admin")
