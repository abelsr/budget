"""transacciones divididas

Revision ID: e4f5a6b7c8d9
Revises: f4a5b6c7d8e9
Create Date: 2026-08-08
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e4f5a6b7c8d9"
down_revision: str | None = "f4a5b6c7d8e9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "transactions",
        sa.Column("is_split", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.drop_constraint("ck_transactions_transfer_shape", "transactions", type_="check")
    op.create_check_constraint(
        "ck_transactions_transfer_shape",
        "transactions",
        "(type = 'transfer' AND category_id IS NULL AND transfer_group_id IS NOT NULL "
        "AND transfer_direction IN ('outflow', 'inflow') AND is_split = false) OR "
        "(type IN ('expense', 'income') AND transfer_group_id IS NULL "
        "AND transfer_direction IS NULL AND ((is_split = false AND category_id IS NOT NULL) "
        "OR (is_split = true AND category_id IS NULL)))",
    )
    op.create_table(
        "transaction_splits",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("transaction_id", sa.String(length=32), nullable=False),
        sa.Column("category_id", sa.String(length=32), nullable=False),
        sa.Column("amount", sa.Numeric(precision=19, scale=4), nullable=False),
        sa.CheckConstraint("amount > 0", name="ck_transaction_splits_positive_amount"),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"]),
        sa.ForeignKeyConstraint(["transaction_id"], ["transactions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("transaction_id", "category_id", name="uq_transaction_splits_transaction_category"),
    )
    op.create_index("ix_transaction_splits_transaction_id", "transaction_splits", ["transaction_id"])
    op.create_index("ix_transaction_splits_category_id", "transaction_splits", ["category_id"])


def downgrade() -> None:
    op.drop_index("ix_transaction_splits_category_id", table_name="transaction_splits")
    op.drop_index("ix_transaction_splits_transaction_id", table_name="transaction_splits")
    op.drop_table("transaction_splits")
    op.drop_constraint("ck_transactions_transfer_shape", "transactions", type_="check")
    op.drop_column("transactions", "is_split")
    op.create_check_constraint(
        "ck_transactions_transfer_shape",
        "transactions",
        "(type = 'transfer' AND category_id IS NULL AND transfer_group_id IS NOT NULL "
        "AND transfer_direction IN ('outflow', 'inflow')) OR "
        "(type IN ('expense', 'income') AND category_id IS NOT NULL "
        "AND transfer_group_id IS NULL AND transfer_direction IS NULL)",
    )
