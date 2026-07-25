"""recurrentes: enlace, autor y día ancla

Tres columnas para poder exponer `recurring_rules`, que hasta ahora existía en
el esquema sin endpoints:

- `transactions.recurring_rule_id`: qué regla generó la transacción (NULL =
  capturada a mano). Alimenta el badge y la trazabilidad.
- `recurring_rules.created_by_id`: a quién se atribuyen las transacciones
  generadas. `transactions.member_id` es NOT NULL y nadie las captura.
- `recurring_rules.anchor_day`: el día del mes que la regla quiere. Sin él, una
  regla del 31 se recorta a 28 al pasar por febrero y se queda ahí para siempre.

`created_by_id` es NOT NULL en el modelo, así que se agrega en tres pasos
(nullable → backfill → alter). En la práctica la tabla está vacía —nunca fue
escribible—, pero el backfill al miembro más antiguo del hogar evita que una
base con filas inesperadas tumbe el despliegue.

Revision ID: 8c41b0e7d2a9
Revises: 673ed5f3d911
Create Date: 2026-07-25 13:24:11.512908

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "8c41b0e7d2a9"
down_revision: str | None = "673ed5f3d911"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "recurring_rules", sa.Column("anchor_day", sa.Integer(), nullable=True)
    )
    op.add_column(
        "recurring_rules",
        sa.Column("created_by_id", sa.String(length=32), nullable=True),
    )
    op.execute(
        "UPDATE recurring_rules AS r SET created_by_id = ("
        "  SELECT u.id FROM users u WHERE u.household_id = r.household_id"
        "  ORDER BY u.created_at, u.id LIMIT 1"
        ") WHERE r.created_by_id IS NULL"
    )
    op.alter_column(
        "recurring_rules",
        "created_by_id",
        existing_type=sa.String(length=32),
        nullable=False,
    )
    op.create_foreign_key(
        "fk_recurring_rules_created_by_id_users",
        "recurring_rules",
        "users",
        ["created_by_id"],
        ["id"],
    )

    op.add_column(
        "transactions",
        sa.Column("recurring_rule_id", sa.String(length=32), nullable=True),
    )
    op.create_index(
        op.f("ix_transactions_recurring_rule_id"),
        "transactions",
        ["recurring_rule_id"],
    )
    op.create_foreign_key(
        "fk_transactions_recurring_rule_id_recurring_rules",
        "transactions",
        "recurring_rules",
        ["recurring_rule_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_transactions_recurring_rule_id_recurring_rules",
        "transactions",
        type_="foreignkey",
    )
    op.drop_index(op.f("ix_transactions_recurring_rule_id"), "transactions")
    op.drop_column("transactions", "recurring_rule_id")

    op.drop_constraint(
        "fk_recurring_rules_created_by_id_users", "recurring_rules", type_="foreignkey"
    )
    op.drop_column("recurring_rules", "created_by_id")
    op.drop_column("recurring_rules", "anchor_day")
