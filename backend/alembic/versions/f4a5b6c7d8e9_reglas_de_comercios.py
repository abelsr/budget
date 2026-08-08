"""reglas de comercios

Revision ID: f4a5b6c7d8e9
Revises: d3e4f5a6b7c8
Create Date: 2026-08-08
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f4a5b6c7d8e9"
down_revision: str | None = "d3e4f5a6b7c8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "merchant_rules",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("household_id", sa.String(length=32), nullable=False),
        sa.Column("pattern", sa.String(length=120), nullable=False),
        sa.Column("match_text", sa.String(length=120), nullable=False),
        sa.Column("category_id", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"]),
        sa.ForeignKeyConstraint(["household_id"], ["households.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("household_id", "match_text", name="uq_merchant_rules_household_match_text"),
    )
    op.create_index("ix_merchant_rules_household_id", "merchant_rules", ["household_id"])
    op.create_index("ix_merchant_rules_category_id", "merchant_rules", ["category_id"])


def downgrade() -> None:
    op.drop_index("ix_merchant_rules_category_id", table_name="merchant_rules")
    op.drop_index("ix_merchant_rules_household_id", table_name="merchant_rules")
    op.drop_table("merchant_rules")
