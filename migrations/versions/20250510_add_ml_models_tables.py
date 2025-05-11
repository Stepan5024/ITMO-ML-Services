"""add_ml_models_tables

Revision ID: 20250510_add_ml_models
Revises: 202310271201
Create Date: 2025-05-10 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID, ENUM
import uuid

revision: str = "20250510_add_ml_models"
down_revision: Union[str, None] = "202310271201"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

model_type = ENUM(
    "classification",
    "regression",
    "clustering",
    "nlp",
    "computer_vision",
    name="modeltype",
    create_type=False,
)

model_algorithm = ENUM(
    "svm",
    "random_forest",
    "logistic_regression",
    "naive_bayes",
    "neural_network",
    "decision_tree",
    "gradient_boosting",
    "knn",
    "linear_regression",
    "k_means",
    name="modelalgorithm",
    create_type=False,
)

model_version_status = ENUM(
    "trained", "testing", "production", name="modelversionstatus", create_type=False
)


def upgrade() -> None:
    connection = op.get_bind()
    op.execute(
        "CREATE TYPE modeltype AS ENUM "
        "('CLASSIFICATION', 'REGRESSION', 'CLUSTERING', 'NLP', 'COMPUTER_VISION')"
    )
    op.execute(
        "CREATE TYPE modelalgorithm AS ENUM "
        "('SVM', 'RANDOM_FOREST', 'LOGISTIC_REGRESSION', 'NAIVE_BAYES', 'NEURAL_NETWORK', "
        "'DECISION_TREE', 'GRADIENT_BOOSTING', 'KNN', 'LINEAR_REGRESSION', 'K_MEANS')"
    )
    op.execute(
        "CREATE TYPE modelversionstatus AS ENUM ('TRAINED', 'TESTING', 'PRODUCTION')"
    )

    model_type.create(connection, checkfirst=True)
    model_algorithm.create(connection, checkfirst=True)
    model_version_status.create(connection, checkfirst=True)

    op.create_table(
        "ml_models",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("name", sa.String(), nullable=False, unique=True),
        sa.Column("description", sa.Text()),
        sa.Column("model_type", model_type, nullable=False),
        sa.Column("algorithm", model_algorithm, nullable=False),
        sa.Column("input_schema", JSONB, nullable=False, default={}),
        sa.Column("output_schema", JSONB, nullable=False, default={}),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("price_per_call", sa.Numeric(10, 2), nullable=False, default=0.0),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )

    op.create_index(op.f("ix_ml_models_name"), "ml_models", ["name"], unique=True)
    op.create_index(
        op.f("ix_ml_models_model_type"), "ml_models", ["model_type"], unique=False
    )

    op.create_table(
        "ml_model_versions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column(
            "model_id",
            UUID(as_uuid=True),
            sa.ForeignKey("ml_models.id"),
            nullable=False,
        ),
        sa.Column("version", sa.String(), nullable=False),
        sa.Column("file_path", sa.String(), nullable=False),
        sa.Column("metrics", JSONB, default={}),
        sa.Column("parameters", JSONB, default={}),
        sa.Column("is_default", sa.Boolean(), default=False),
        sa.Column(
            "created_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False
        ),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("status", model_version_status, default="trained", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )

    op.create_index(
        op.f("ix_ml_model_versions_model_id"),
        "ml_model_versions",
        ["model_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_ml_model_versions_model_id_version"),
        "ml_model_versions",
        ["model_id", "version"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_ml_model_versions_model_id_version"), table_name="ml_model_versions"
    )
    op.drop_index(op.f("ix_ml_model_versions_model_id"), table_name="ml_model_versions")
    op.drop_table("ml_model_versions")

    op.drop_index(op.f("ix_ml_models_model_type"), table_name="ml_models")
    op.drop_index(op.f("ix_ml_models_name"), table_name="ml_models")
    op.drop_table("ml_models")

    connection = op.get_bind()
    model_version_status.drop(connection, checkfirst=True)
    model_algorithm.drop(connection, checkfirst=True)
    model_type.drop(connection, checkfirst=True)
