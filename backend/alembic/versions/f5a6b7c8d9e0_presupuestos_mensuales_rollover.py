"""presupuestos mensuales con rollover

Revision ID: f5a6b7c8d9e0
Revises: e4f5a6b7c8d9
Create Date: 2026-08-08
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f5a6b7c8d9e0"
down_revision: str | None = "e4f5a6b7c8d9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("budgets_household_id_category_id_key", "budgets", type_="unique")
    op.add_column("budgets", sa.Column("month", sa.Date(), nullable=True))
    op.add_column(
        "budgets",
        sa.Column("rollover", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.create_unique_constraint(
        "uq_budgets_household_category_month",
        "budgets",
        ["household_id", "category_id", "month"],
    )
    op.create_index(
        "uq_budgets_household_category_global",
        "budgets",
        ["household_id", "category_id"],
        unique=True,
        postgresql_where=sa.text("month IS NULL"),
    )
    op.alter_column("budgets", "rollover", server_default=None)


def downgrade() -> None:
    op.drop_index("uq_budgets_household_category_global", table_name="budgets")
    op.drop_constraint("uq_budgets_household_category_month", "budgets", type_="unique")
    op.drop_column("budgets", "rollover")
    op.drop_column("budgets", "month")
    op.create_unique_constraint(
        "budgets_household_id_category_id_key", "budgets", ["household_id", "category_id"]
    )
