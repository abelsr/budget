"""metas de ahorro

Revision ID: 0d8f96b4a731
Revises: c14a8d2e9f31
Create Date: 2026-08-05
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0d8f96b4a731"
down_revision: str | None = "c14a8d2e9f31"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "savings_goals",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("household_id", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("target_amount", sa.Numeric(precision=19, scale=4), nullable=False),
        sa.Column("current_amount", sa.Numeric(precision=19, scale=4), nullable=False, server_default="0"),
        sa.Column("target_date", sa.Date(), nullable=True),
        sa.Column("account_id", sa.String(length=32), nullable=True),
        sa.Column("icon", sa.String(length=60), nullable=False, server_default="piggy-bank"),
        sa.Column("color", sa.String(length=7), nullable=False, server_default="#30b0c7"),
        sa.Column("archived", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["household_id"], ["households.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_savings_goals_household_id", "savings_goals", ["household_id"])
    op.create_index("ix_savings_goals_account_id", "savings_goals", ["account_id"])


def downgrade() -> None:
    op.drop_index("ix_savings_goals_account_id", table_name="savings_goals")
    op.drop_index("ix_savings_goals_household_id", table_name="savings_goals")
    op.drop_table("savings_goals")
