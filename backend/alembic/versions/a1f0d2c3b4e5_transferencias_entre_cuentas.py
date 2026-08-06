"""transferencias entre cuentas

Revision ID: a1f0d2c3b4e5
Revises: e2f4a6b8c0d2
Create Date: 2026-08-05
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a1f0d2c3b4e5"
down_revision: str | None = "e2f4a6b8c0d2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "transfer_groups",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("household_id", sa.String(length=32), nullable=False),
        sa.Column("client_id", sa.String(length=36), nullable=True),
        sa.Column("created_by_id", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["household_id"], ["households.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("household_id", "client_id", name="uq_transfer_groups_household_client_id"),
    )
    op.create_index("ix_transfer_groups_household_id", "transfer_groups", ["household_id"])
    op.alter_column("transactions", "category_id", existing_type=sa.String(length=32), nullable=True)
    op.add_column("transactions", sa.Column("transfer_group_id", sa.String(length=32), nullable=True))
    op.add_column("transactions", sa.Column("transfer_direction", sa.String(length=10), nullable=True))
    op.create_foreign_key("fk_transactions_transfer_group", "transactions", "transfer_groups", ["transfer_group_id"], ["id"])
    op.create_index("ix_transactions_transfer_group_id", "transactions", ["transfer_group_id"])
    op.create_check_constraint(
        "ck_transactions_transfer_shape",
        "transactions",
        "(type = 'transfer' AND category_id IS NULL AND transfer_group_id IS NOT NULL "
        "AND transfer_direction IN ('outflow', 'inflow')) OR "
        "(type IN ('expense', 'income') AND category_id IS NOT NULL "
        "AND transfer_group_id IS NULL AND transfer_direction IS NULL)",
    )


def downgrade() -> None:
    op.drop_constraint("ck_transactions_transfer_shape", "transactions", type_="check")
    op.drop_index("ix_transactions_transfer_group_id", table_name="transactions")
    op.drop_constraint("fk_transactions_transfer_group", "transactions", type_="foreignkey")
    op.drop_column("transactions", "transfer_direction")
    op.drop_column("transactions", "transfer_group_id")
    op.alter_column("transactions", "category_id", existing_type=sa.String(length=32), nullable=False)
    op.drop_index("ix_transfer_groups_household_id", table_name="transfer_groups")
    op.drop_table("transfer_groups")
