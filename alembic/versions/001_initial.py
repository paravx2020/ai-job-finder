"""Initial migration: create users, job_postings, applications, cv_improvement_logs.

Revision ID: 001_initial
Revises:
Create Date: 2026-05-16 12:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("raw_cv_path", sa.String(length=500), nullable=True),
        sa.Column("parsed_cv", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_table(
        "job_postings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=50), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("company", sa.String(length=255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("url", sa.String(length=1000), nullable=True),
        sa.Column("salary", sa.String(length=100), nullable=True),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("posted_date", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "applications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("job_id", sa.Integer(), sa.ForeignKey("job_postings.id"), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=True),
        sa.Column("match_score", sa.Float(), nullable=True),
        sa.Column("match_reason", sa.Text(), nullable=True),
        sa.Column("applied_at", sa.DateTime(), nullable=True),
        sa.Column("response", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "cv_improvement_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("section", sa.String(length=100), nullable=True),
        sa.Column("original_text", sa.Text(), nullable=True),
        sa.Column("improved_text", sa.Text(), nullable=True),
        sa.Column("model_used", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("cv_improvement_logs")
    op.drop_table("applications")
    op.drop_table("job_postings")
    op.drop_table("users")
