"""presupuestos

Tabla `budgets`: límite de gasto por categoría, global (no por mes) — ver
`app.models.Budget`. `UniqueConstraint(household_id, category_id)` es lo que
impide un segundo límite para la misma categoría; el endpoint la traduce a un
409 en vez de dejar que la excepción de integridad llegue cruda.

Revision ID: a8f22761d428
Revises: 8c41b0e7d2a9
Create Date: 2026-07-25 21:25:59.466611

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "a8f22761d428"
down_revision: str | None = "8c41b0e7d2a9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "budgets",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("household_id", sa.String(length=32), nullable=False),
        sa.Column("category_id", sa.String(length=32), nullable=False),
        sa.Column("amount", sa.Numeric(precision=19, scale=4), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"]),
        sa.ForeignKeyConstraint(["household_id"], ["households.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("household_id", "category_id"),
    )
    op.create_index(
        "ix_budgets_household_id", "budgets", ["household_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_budgets_household_id", table_name="budgets")
    op.drop_table("budgets")
