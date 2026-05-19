"""Add last_scraped column and unique URL constraint to job_postings.

Revision ID: 002_add_constraints
Revises: 001_initial
Create Date: 2026-05-16
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "002_add_constraints"
down_revision: str | None = "001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add last_scraped column
    op.add_column("job_postings", sa.Column("last_scraped", sa.DateTime(), nullable=True))

    # Note: SQLite doesn't support ALTER TABLE ADD CONSTRAINT directly.
    # For the unique constraint on url, we need to recreate the table.
    # Using batch operations for SQLite compatibility.
    with op.batch_alter_table("job_postings") as batch_op:
        batch_op.create_unique_constraint("uq_job_postings_url", ["url"])


def downgrade() -> None:
    with op.batch_alter_table("job_postings") as batch_op:
        batch_op.drop_constraint("uq_job_postings_url", type_="unique")

    op.drop_column("job_postings", "last_scraped")
