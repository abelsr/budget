"""perfil de usuario

Revision ID: e52fa631c4bd
Revises: b91f3c6d7e20
Create Date: 2026-08-04

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "e52fa631c4bd"
down_revision: str | None = "b91f3c6d7e20"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("sex", sa.String(length=20), nullable=True))
    op.add_column("users", sa.Column("birth_date", sa.Date(), nullable=True))
    op.add_column("users", sa.Column("avatar_path", sa.String(length=500), nullable=True))
    op.add_column(
        "users", sa.Column("avatar_updated_at", sa.DateTime(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("users", "avatar_updated_at")
    op.drop_column("users", "avatar_path")
    op.drop_column("users", "birth_date")
    op.drop_column("users", "sex")
