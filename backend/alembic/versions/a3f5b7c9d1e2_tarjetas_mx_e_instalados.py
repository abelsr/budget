"""cuentas de tarjeta y planes de instalados

Revision ID: a3f5b7c9d1e2
Revises: c7d8e9f0a1b2
Create Date: 2026-08-16
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a3f5b7c9d1e2"
down_revision: str | None = "c7d8e9f0a1b2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("accounts", sa.Column("statement_day", sa.Integer(), nullable=True))
    op.add_column("accounts", sa.Column("payment_due_days", sa.Integer(), nullable=True))
    op.create_check_constraint(
        "ck_accounts_statement_day", "accounts", "statement_day IS NULL OR (statement_day >= 1 AND statement_day <= 28)"
    )
    op.create_check_constraint(
        "ck_accounts_payment_due_days", "accounts", "payment_due_days IS NULL OR (payment_due_days >= 1 AND payment_due_days <= 60)"
    )
    op.create_table(
        "instalment_plans",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column("household_id", sa.String(length=32), sa.ForeignKey("households.id"), nullable=False),
        sa.Column("account_id", sa.String(length=32), sa.ForeignKey("accounts.id"), nullable=False),
        sa.Column("source_transaction_id", sa.String(length=32), sa.ForeignKey("transactions.id"), nullable=False),
        sa.Column("months", sa.Integer(), nullable=False),
        sa.Column("total_amount", sa.Numeric(precision=19, scale=4), nullable=False),
        sa.Column("monthly_amount", sa.Numeric(precision=19, scale=4), nullable=False),
        sa.Column("first_due_date", sa.Date(), nullable=False),
        sa.Column("paid_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=12), nullable=False, server_default="active"),
        sa.Column("created_by_id", sa.String(length=32), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("household_id", "source_transaction_id", name="uq_instalment_plans_household_source"),
        sa.CheckConstraint("months >= 2 AND months <= 48", name="ck_instalment_plans_months"),
        sa.CheckConstraint("status IN ('active', 'paused', 'completed', 'cancelled')", name="ck_instalment_plans_status"),
    )
    op.create_index("ix_instalment_plans_household_id", "instalment_plans", ["household_id"])
    op.create_index("ix_instalment_plans_account_id", "instalment_plans", ["account_id"])


def downgrade() -> None:
    op.drop_index("ix_instalment_plans_account_id", table_name="instalment_plans")
    op.drop_index("ix_instalment_plans_household_id", table_name="instalment_plans")
    op.drop_table("instalment_plans")
    op.drop_constraint("ck_accounts_payment_due_days", "accounts", type_="check")
    op.drop_constraint("ck_accounts_statement_day", "accounts", type_="check")
    op.drop_column("accounts", "payment_due_days")
    op.drop_column("accounts", "statement_day")
