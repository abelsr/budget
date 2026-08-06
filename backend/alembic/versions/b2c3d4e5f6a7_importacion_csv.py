"""importacion CSV

Revision ID: b2c3d4e5f6a7
Revises: a1f0d2c3b4e5
Create Date: 2026-08-05
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b2c3d4e5f6a7"
down_revision: str | None = "a1f0d2c3b4e5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_unique_constraint("uq_accounts_id_household_id", "accounts", ["id", "household_id"])
    op.create_table(
        "import_batches",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("household_id", sa.String(length=32), nullable=False),
        sa.Column("account_id", sa.String(length=32), nullable=False),
        sa.Column("created_by_id", sa.String(length=32), nullable=False),
        sa.Column("source_filename", sa.String(length=255), nullable=False),
        sa.Column("mapping", sa.JSON(), nullable=False),
        sa.Column("selected_count", sa.Integer(), nullable=False),
        sa.Column("imported_count", sa.Integer(), nullable=False),
        sa.Column("skipped_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["account_id", "household_id"],
            ["accounts.id", "accounts.household_id"],
            name="fk_import_batches_account_household",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_id", "household_id"],
            ["users.id", "users.household_id"],
            name="fk_import_batches_creator_membership",
        ),
        sa.ForeignKeyConstraint(
            ["household_id"],
            ["households.id"],
            name="fk_import_batches_household",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "id",
            "household_id",
            "account_id",
            name="uq_import_batches_id_household_account",
        ),
    )
    op.create_index("ix_import_batches_account_id", "import_batches", ["account_id"])
    op.create_index("ix_import_batches_household_id", "import_batches", ["household_id"])
    op.add_column("transactions", sa.Column("import_batch_id", sa.String(length=32), nullable=True))
    op.add_column("transactions", sa.Column("deleted_at", sa.DateTime(), nullable=True))
    op.add_column("transactions", sa.Column("delete_reason", sa.String(length=30), nullable=True))
    op.create_foreign_key(
        "fk_transactions_import_batch_scope",
        "transactions",
        "import_batches",
        ["import_batch_id", "household_id", "account_id"],
        ["id", "household_id", "account_id"],
    )
    op.create_unique_constraint(
        "uq_transactions_id_import_batch_id",
        "transactions",
        ["id", "import_batch_id"],
    )
    op.create_index("ix_transactions_import_batch_id", "transactions", ["import_batch_id"])
    op.create_table(
        "import_rows",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("batch_id", sa.String(length=32), nullable=False),
        sa.Column("source_position", sa.Integer(), nullable=False),
        sa.Column("source_snapshot", sa.JSON(), nullable=False),
        sa.Column("transaction_baseline", sa.JSON(), nullable=False),
        sa.Column("advisory_reasons", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("transaction_id", sa.String(length=32), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["batch_id"],
            ["import_batches.id"],
            name="fk_import_rows_batch",
        ),
        sa.ForeignKeyConstraint(
            ["transaction_id", "batch_id"],
            ["transactions.id", "transactions.import_batch_id"],
            name="fk_import_rows_transaction_batch",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("batch_id", "source_position", name="uq_import_rows_batch_position"),
        sa.UniqueConstraint(
            "id",
            "batch_id",
            "transaction_id",
            name="uq_import_rows_id_batch_transaction",
        ),
    )
    op.create_index("ix_import_rows_batch_id", "import_rows", ["batch_id"])
    op.create_index("ix_import_rows_transaction_id", "import_rows", ["transaction_id"])
    op.create_table(
        "import_fingerprints",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("batch_id", sa.String(length=32), nullable=False),
        sa.Column("household_id", sa.String(length=32), nullable=False),
        sa.Column("account_id", sa.String(length=32), nullable=False),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column("import_row_id", sa.String(length=32), nullable=False),
        sa.Column("transaction_id", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["batch_id", "household_id", "account_id"],
            [
                "import_batches.id",
                "import_batches.household_id",
                "import_batches.account_id",
            ],
            name="fk_import_fingerprints_batch_scope",
        ),
        sa.ForeignKeyConstraint(
            ["import_row_id", "batch_id", "transaction_id"],
            [
                "import_rows.id",
                "import_rows.batch_id",
                "import_rows.transaction_id",
            ],
            name="fk_import_fingerprints_row_transaction",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "household_id",
            "account_id",
            "fingerprint",
            name="uq_import_fingerprints_household_account_fingerprint",
        ),
    )
    op.create_index("ix_import_fingerprints_account_id", "import_fingerprints", ["account_id"])
    op.create_index("ix_import_fingerprints_batch_id", "import_fingerprints", ["batch_id"])
    op.create_index("ix_import_fingerprints_household_id", "import_fingerprints", ["household_id"])
    op.create_index("ix_import_fingerprints_import_row_id", "import_fingerprints", ["import_row_id"])
    op.create_index("ix_import_fingerprints_transaction_id", "import_fingerprints", ["transaction_id"])
    op.create_table(
        "transaction_edit_events",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("transaction_id", sa.String(length=32), nullable=False),
        sa.Column("edited_by_id", sa.String(length=32), nullable=False),
        sa.Column("before_snapshot", sa.JSON(), nullable=False),
        sa.Column("after_snapshot", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["edited_by_id"],
            ["users.id"],
            name="fk_transaction_edit_events_editor",
        ),
        sa.ForeignKeyConstraint(
            ["transaction_id"],
            ["transactions.id"],
            name="fk_transaction_edit_events_transaction",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_transaction_edit_events_transaction_id", "transaction_edit_events", ["transaction_id"])


def downgrade() -> None:
    op.drop_index("ix_transaction_edit_events_transaction_id", table_name="transaction_edit_events")
    op.drop_table("transaction_edit_events")
    op.drop_index("ix_import_fingerprints_transaction_id", table_name="import_fingerprints")
    op.drop_index("ix_import_fingerprints_import_row_id", table_name="import_fingerprints")
    op.drop_index("ix_import_fingerprints_household_id", table_name="import_fingerprints")
    op.drop_index("ix_import_fingerprints_batch_id", table_name="import_fingerprints")
    op.drop_index("ix_import_fingerprints_account_id", table_name="import_fingerprints")
    op.drop_table("import_fingerprints")
    op.drop_index("ix_import_rows_transaction_id", table_name="import_rows")
    op.drop_index("ix_import_rows_batch_id", table_name="import_rows")
    op.drop_table("import_rows")
    op.drop_index("ix_transactions_import_batch_id", table_name="transactions")
    op.drop_constraint("uq_transactions_id_import_batch_id", "transactions", type_="unique")
    op.drop_constraint("fk_transactions_import_batch_scope", "transactions", type_="foreignkey")
    op.drop_column("transactions", "delete_reason")
    op.drop_column("transactions", "deleted_at")
    op.drop_column("transactions", "import_batch_id")
    op.drop_index("ix_import_batches_household_id", table_name="import_batches")
    op.drop_index("ix_import_batches_account_id", table_name="import_batches")
    op.drop_table("import_batches")
    op.drop_constraint("uq_accounts_id_household_id", "accounts", type_="unique")
