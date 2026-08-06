"""cuentas personales

Revision ID: 4f5d2a8b9c10
Revises: 0d8f96b4a731
Create Date: 2026-08-05
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "4f5d2a8b9c10"
down_revision: str | None = "0d8f96b4a731"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Existing rows deliberately remain shared: owner_id defaults to NULL.
    op.add_column("accounts", sa.Column("owner_id", sa.String(length=32), nullable=True))
    op.create_index("ix_accounts_owner_id", "accounts", ["owner_id"])
    op.create_foreign_key(
        "fk_accounts_owner_membership",
        "accounts",
        "users",
        ["owner_id", "household_id"],
        ["id", "household_id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_accounts_owner_membership", "accounts", type_="foreignkey")
    op.drop_index("ix_accounts_owner_id", table_name="accounts")
    op.drop_column("accounts", "owner_id")
