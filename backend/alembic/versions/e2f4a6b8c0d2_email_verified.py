"""add email verification state

Revision ID: e2f4a6b8c0d2
Revises: 9b7e6c5d4a3f
Create Date: 2026-08-05
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e2f4a6b8c0d2"
down_revision: str | None = "9b7e6c5d4a3f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("email_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("users", "email_verified")
