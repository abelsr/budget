"""cuentas_banco_y_tarjeta

Columnas opcionales de tarjeta en `accounts`: `bank` (nombre del banco),
`card_brand` (visa|mastercard|amex|other) y `last_four` (últimos 4 dígitos).
Solo metadatos de presentación: si se definen, el widget de la cuenta se dibuja
como tarjeta tipo wallet (docs/roadmap/18-features-y-uiux-propuestas.md B1).
Nunca se guarda el número completo de tarjeta.

Revision ID: 7948fa86c19b
Revises: a8f22761d428
Create Date: 2026-08-03 23:17:46.186378

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "7948fa86c19b"
down_revision: str | None = "a8f22761d428"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("accounts", sa.Column("bank", sa.String(length=60), nullable=True))
    op.add_column(
        "accounts", sa.Column("card_brand", sa.String(length=10), nullable=True)
    )
    op.add_column("accounts", sa.Column("last_four", sa.String(length=4), nullable=True))


def downgrade() -> None:
    op.drop_column("accounts", "last_four")
    op.drop_column("accounts", "card_brand")
    op.drop_column("accounts", "bank")
