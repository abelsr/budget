"""propietario de hogar con excepción para hogares legados huérfanos.

Los hogares existentes que ya no tienen miembros se conservan con owner_id NULL:
no hay una persona legítima a quien asignar la propiedad. Los hogares activos se
rellenan con su miembro más antiguo y los nuevos siempre reciben propietario.

Revision ID: c14a8d2e9f31
Revises: e52fa631c4bd
Create Date: 2026-08-05

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c14a8d2e9f31"
down_revision: str | None = "e52fa631c4bd"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("households", sa.Column("owner_id", sa.String(length=32), nullable=True))
    # Un hogar sin miembros queda NULL de forma intencional: es un registro
    # legado inaccesible, no se inventa ni elimina un usuario para migrarlo.
    op.execute(
        """
        UPDATE households AS household
        SET owner_id = (
            SELECT member.id
            FROM users AS member
            WHERE member.household_id = household.id
            ORDER BY member.created_at ASC, member.id ASC
            LIMIT 1
        )
        """
    )
    op.create_unique_constraint("uq_users_id_household_id", "users", ["id", "household_id"])
    # Es diferible para permitir registrar usuario y hogar en la misma
    # transacción: el usuario recibe household_id antes del commit.
    op.create_foreign_key(
        "fk_households_owner_membership",
        "households",
        "users",
        ["owner_id", "id"],
        ["id", "household_id"],
        deferrable=True,
        initially="DEFERRED",
    )


def downgrade() -> None:
    op.drop_constraint("fk_households_owner_membership", "households", type_="foreignkey")
    op.drop_constraint("uq_users_id_household_id", "users", type_="unique")
    op.drop_column("households", "owner_id")
