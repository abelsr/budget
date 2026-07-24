"""onboarding_completed_at en users

Flag del wizard inicial: NULL = pendiente.

Los usuarios que ya existían son anteriores a la feature y tienen su hogar
configurado, así que se marcan como completados en el mismo paso; si no, al
desplegar verían un wizard que no les toca. Los usuarios nuevos entran con NULL
por el default de la columna.

Revision ID: 673ed5f3d911
Revises: 5d15cfc79c35
Create Date: 2026-07-24 15:58:52.090596

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "673ed5f3d911"
down_revision: str | None = "5d15cfc79c35"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users", sa.Column("onboarding_completed_at", sa.DateTime(), nullable=True)
    )
    op.execute(
        "UPDATE users SET onboarding_completed_at = CURRENT_TIMESTAMP "
        "WHERE onboarding_completed_at IS NULL"
    )


def downgrade() -> None:
    op.drop_column("users", "onboarding_completed_at")
