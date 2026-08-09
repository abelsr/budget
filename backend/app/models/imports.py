from datetime import datetime

from sqlalchemy import DateTime, ForeignKeyConstraint, JSON, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.identity import new_id


class ImportBatch(Base):
    __tablename__ = "import_batches"
    __table_args__ = (
        UniqueConstraint("id", "household_id", "account_id", name="uq_import_batches_id_household_account"),
        ForeignKeyConstraint(["account_id", "household_id"], ["accounts.id", "accounts.household_id"], name="fk_import_batches_account_household"),
        ForeignKeyConstraint(["created_by_id", "household_id"], ["users.id", "users.household_id"], name="fk_import_batches_creator_membership"),
        ForeignKeyConstraint(["household_id"], ["households.id"], name="fk_import_batches_household"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    household_id: Mapped[str] = mapped_column(String(32), index=True)
    account_id: Mapped[str] = mapped_column(String(32), index=True)
    created_by_id: Mapped[str] = mapped_column(String(32))
    source_filename: Mapped[str] = mapped_column(String(255))
    mapping: Mapped[dict] = mapped_column(JSON)
    selected_count: Mapped[int] = mapped_column()
    imported_count: Mapped[int] = mapped_column()
    skipped_count: Mapped[int] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class ImportRow(Base):
    __tablename__ = "import_rows"
    __table_args__ = (
        UniqueConstraint("batch_id", "source_position", name="uq_import_rows_batch_position"),
        UniqueConstraint("id", "batch_id", "transaction_id", name="uq_import_rows_id_batch_transaction"),
        ForeignKeyConstraint(["transaction_id", "batch_id"], ["transactions.id", "transactions.import_batch_id"], name="fk_import_rows_transaction_batch"),
        ForeignKeyConstraint(["batch_id"], ["import_batches.id"], name="fk_import_rows_batch"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    batch_id: Mapped[str] = mapped_column(String(32), index=True)
    source_position: Mapped[int] = mapped_column()
    source_snapshot: Mapped[dict] = mapped_column(JSON)
    transaction_baseline: Mapped[dict] = mapped_column(JSON)
    advisory_reasons: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(20))
    transaction_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class ImportFingerprint(Base):
    __tablename__ = "import_fingerprints"
    __table_args__ = (
        UniqueConstraint("household_id", "account_id", "fingerprint", name="uq_import_fingerprints_household_account_fingerprint"),
        ForeignKeyConstraint(["batch_id", "household_id", "account_id"], ["import_batches.id", "import_batches.household_id", "import_batches.account_id"], name="fk_import_fingerprints_batch_scope"),
        ForeignKeyConstraint(["import_row_id", "batch_id", "transaction_id"], ["import_rows.id", "import_rows.batch_id", "import_rows.transaction_id"], name="fk_import_fingerprints_row_transaction"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    batch_id: Mapped[str] = mapped_column(String(32), index=True)
    household_id: Mapped[str] = mapped_column(String(32), index=True)
    account_id: Mapped[str] = mapped_column(String(32), index=True)
    fingerprint: Mapped[str] = mapped_column(String(64))
    import_row_id: Mapped[str] = mapped_column(String(32), index=True)
    transaction_id: Mapped[str] = mapped_column(String(32), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
