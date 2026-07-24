"""esquema inicial

Las 8 tablas del MVP, equivalentes a lo que producía
`Base.metadata.create_all` antes de adoptar Alembic.

Nota: los `created_at` usan `sa.func.now()` (no un literal SQL) para que cada
dialecto genere su propio default —`now()` en Postgres, `CURRENT_TIMESTAMP` en
SQLite—, igual que hacían los modelos. Autogenerate los había renderizado como
literal de SQLite; se corrigieron a mano.

Revision ID: 5d15cfc79c35
Revises:
Create Date: 2026-07-24 15:54:33.386372

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "5d15cfc79c35"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "households",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("currency_code", sa.String(length=3), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "accounts",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("household_id", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column(
            "opening_balance", sa.Numeric(precision=19, scale=4), nullable=False
        ),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["household_id"], ["households.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_accounts_household_id", "accounts", ["household_id"], unique=False
    )
    op.create_table(
        "categories",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("household_id", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("icon", sa.String(length=60), nullable=False),
        sa.Column("color", sa.String(length=7), nullable=False),
        sa.Column("type", sa.String(length=10), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["household_id"], ["households.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_categories_household_id", "categories", ["household_id"], unique=False
    )
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("household_id", sa.String(length=32), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["household_id"], ["households.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_table(
        "invitations",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("household_id", sa.String(length=32), nullable=False),
        sa.Column("token", sa.String(length=64), nullable=False),
        sa.Column("created_by_id", sa.String(length=32), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("used_at", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["household_id"], ["households.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token"),
    )
    op.create_table(
        "recurring_rules",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("household_id", sa.String(length=32), nullable=False),
        sa.Column("type", sa.String(length=10), nullable=False),
        sa.Column("amount", sa.Numeric(precision=19, scale=4), nullable=False),
        sa.Column("category_id", sa.String(length=32), nullable=False),
        sa.Column("account_id", sa.String(length=32), nullable=False),
        sa.Column("frequency", sa.String(length=10), nullable=False),
        sa.Column("next_run_date", sa.Date(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"]),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"]),
        sa.ForeignKeyConstraint(["household_id"], ["households.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_recurring_rules_household_id",
        "recurring_rules",
        ["household_id"],
        unique=False,
    )
    op.create_table(
        "transactions",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("household_id", sa.String(length=32), nullable=False),
        sa.Column("type", sa.String(length=10), nullable=False),
        sa.Column("amount", sa.Numeric(precision=19, scale=4), nullable=False),
        sa.Column("category_id", sa.String(length=32), nullable=False),
        sa.Column("account_id", sa.String(length=32), nullable=False),
        sa.Column("member_id", sa.String(length=32), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"]),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"]),
        sa.ForeignKeyConstraint(["household_id"], ["households.id"]),
        sa.ForeignKeyConstraint(["member_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_transactions_account_id", "transactions", ["account_id"], unique=False
    )
    op.create_index("ix_transactions_date", "transactions", ["date"], unique=False)
    op.create_index(
        "ix_transactions_household_id", "transactions", ["household_id"], unique=False
    )
    op.create_table(
        "attachments",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("transaction_id", sa.String(length=32), nullable=False),
        sa.Column("household_id", sa.String(length=32), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=120), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("storage_path", sa.String(length=500), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["household_id"], ["households.id"]),
        sa.ForeignKeyConstraint(["transaction_id"], ["transactions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_attachments_household_id", "attachments", ["household_id"], unique=False
    )
    op.create_index(
        "ix_attachments_transaction_id", "attachments", ["transaction_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_attachments_transaction_id", table_name="attachments")
    op.drop_index("ix_attachments_household_id", table_name="attachments")
    op.drop_table("attachments")
    op.drop_index("ix_transactions_household_id", table_name="transactions")
    op.drop_index("ix_transactions_date", table_name="transactions")
    op.drop_index("ix_transactions_account_id", table_name="transactions")
    op.drop_table("transactions")
    op.drop_index("ix_recurring_rules_household_id", table_name="recurring_rules")
    op.drop_table("recurring_rules")
    op.drop_table("invitations")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
    op.drop_index("ix_categories_household_id", table_name="categories")
    op.drop_table("categories")
    op.drop_index("ix_accounts_household_id", table_name="accounts")
    op.drop_table("accounts")
    op.drop_table("households")
