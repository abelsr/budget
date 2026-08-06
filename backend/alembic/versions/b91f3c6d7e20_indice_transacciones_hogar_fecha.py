"""indice de transacciones por hogar y fecha

Revision ID: b91f3c6d7e20
Revises: 7948fa86c19b
Create Date: 2026-08-04

"""

from collections.abc import Sequence

from alembic import op

revision: str = "b91f3c6d7e20"
down_revision: str | None = "7948fa86c19b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_transactions_household_date",
        "transactions",
        ["household_id", "date"],
    )


def downgrade() -> None:
    op.drop_index("ix_transactions_household_date", table_name="transactions")
