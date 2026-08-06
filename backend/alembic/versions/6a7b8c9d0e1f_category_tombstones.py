"""category tombstones

Revision ID: 6a7b8c9d0e1f
Revises: 4f5d2a8b9c10
Create Date: 2026-08-05
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "6a7b8c9d0e1f"
down_revision: str | None = "4f5d2a8b9c10"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "categories",
        sa.Column("deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.alter_column("categories", "deleted", server_default=None)


def downgrade() -> None:
    op.drop_column("categories", "deleted")
