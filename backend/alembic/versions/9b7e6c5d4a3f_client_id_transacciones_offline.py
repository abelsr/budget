"""client id para transacciones offline

Revision ID: 9b7e6c5d4a3f
Revises: 6a7b8c9d0e1f
Create Date: 2026-08-05
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "9b7e6c5d4a3f"
down_revision: str | None = "6a7b8c9d0e1f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("transactions", sa.Column("client_id", sa.String(length=36), nullable=True))
    op.create_unique_constraint(
        "uq_transactions_household_client_id",
        "transactions",
        ["household_id", "client_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_transactions_household_client_id", "transactions", type_="unique")
    op.drop_column("transactions", "client_id")
