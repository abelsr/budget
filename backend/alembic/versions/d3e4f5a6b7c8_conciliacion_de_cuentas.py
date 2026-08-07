"""conciliacion de cuentas

Revision ID: d3e4f5a6b7c8
Revises: b2c3d4e5f6a7
Create Date: 2026-08-06
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d3e4f5a6b7c8"
down_revision: str | None = "b2c3d4e5f6a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "reconciliation_sessions",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("account_id", sa.String(length=32), nullable=False),
        sa.Column("household_id", sa.String(length=32), nullable=False),
        sa.Column("statement_date", sa.Date(), nullable=False),
        sa.Column("statement_balance", sa.Numeric(precision=19, scale=4), nullable=False),
        sa.Column("status", sa.String(length=12), server_default="open", nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("created_by_id", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"]),
        sa.ForeignKeyConstraint(["household_id"], ["households.id"]),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_reconciliation_sessions_account_id", "reconciliation_sessions", ["account_id"])
    op.create_index("ix_reconciliation_sessions_household_id", "reconciliation_sessions", ["household_id"])
    op.add_column("transactions", sa.Column("reconciliation_status", sa.String(length=12), server_default="pending", nullable=False))
    op.add_column("transactions", sa.Column("reconciliation_session_id", sa.String(length=32), nullable=True))
    op.create_foreign_key("fk_transactions_reconciliation_session", "transactions", "reconciliation_sessions", ["reconciliation_session_id"], ["id"])
    op.create_index("ix_transactions_reconciliation_session_id", "transactions", ["reconciliation_session_id"])


def downgrade() -> None:
    op.drop_index("ix_transactions_reconciliation_session_id", table_name="transactions")
    op.drop_constraint("fk_transactions_reconciliation_session", "transactions", type_="foreignkey")
    op.drop_column("transactions", "reconciliation_session_id")
    op.drop_column("transactions", "reconciliation_status")
    op.drop_index("ix_reconciliation_sessions_household_id", table_name="reconciliation_sessions")
    op.drop_index("ix_reconciliation_sessions_account_id", table_name="reconciliation_sessions")
    op.drop_table("reconciliation_sessions")
