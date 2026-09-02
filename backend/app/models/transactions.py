from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, ForeignKeyConstraint, Index, JSON, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.identity import new_id


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        Index("ix_transactions_household_date", "household_id", "date"),
        UniqueConstraint("household_id", "client_id", name="uq_transactions_household_client_id"),
        UniqueConstraint("id", "import_batch_id", name="uq_transactions_id_import_batch_id"),
        ForeignKeyConstraint(["import_batch_id", "household_id", "account_id"], ["import_batches.id", "import_batches.household_id", "import_batches.account_id"], name="fk_transactions_import_batch_scope"),
        CheckConstraint("(type = 'transfer' AND category_id IS NULL AND transfer_group_id IS NOT NULL AND transfer_direction IN ('outflow', 'inflow') AND is_split = false) OR (type IN ('expense', 'income') AND transfer_group_id IS NULL AND transfer_direction IS NULL AND ((is_split = false AND category_id IS NOT NULL) OR (is_split = true AND category_id IS NULL)))", name="ck_transactions_transfer_shape"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    household_id: Mapped[str] = mapped_column(ForeignKey("households.id"), index=True)
    client_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    type: Mapped[str] = mapped_column(String(10))
    amount: Mapped[Decimal] = mapped_column(Numeric(19, 4))
    category_id: Mapped[str | None] = mapped_column(ForeignKey("categories.id"), nullable=True)
    is_split: Mapped[bool] = mapped_column(default=False, server_default="false")
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), index=True)
    transfer_group_id: Mapped[str | None] = mapped_column(ForeignKey("transfer_groups.id"), nullable=True, index=True)
    transfer_direction: Mapped[str | None] = mapped_column(String(10), nullable=True)
    member_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    date: Mapped[date] = mapped_column(Date, index=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    recurring_rule_id: Mapped[str | None] = mapped_column(ForeignKey("recurring_rules.id"), nullable=True, index=True)
    import_batch_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    delete_reason: Mapped[str | None] = mapped_column(String(30), nullable=True)
    reconciliation_status: Mapped[str] = mapped_column(String(12), default="pending", server_default="pending")
    reconciliation_session_id: Mapped[str | None] = mapped_column(ForeignKey("reconciliation_sessions.id"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    attachments: Mapped[list["Attachment"]] = relationship(lazy="selectin")
    splits: Mapped[list["TransactionSplit"]] = relationship(back_populates="transaction", lazy="selectin", cascade="all, delete-orphan")
    author: Mapped["User"] = relationship(foreign_keys=[member_id], lazy="selectin")


class TransactionSplit(Base):
    __tablename__ = "transaction_splits"
    __table_args__ = (
        UniqueConstraint("transaction_id", "category_id", name="uq_transaction_splits_transaction_category"),
        CheckConstraint("amount > 0", name="ck_transaction_splits_positive_amount"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    transaction_id: Mapped[str] = mapped_column(ForeignKey("transactions.id", ondelete="CASCADE"), index=True)
    category_id: Mapped[str] = mapped_column(ForeignKey("categories.id"), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(19, 4))

    transaction: Mapped[Transaction] = relationship(back_populates="splits")
    category: Mapped["Category"] = relationship(lazy="joined")


class ReconciliationSession(Base):
    __tablename__ = "reconciliation_sessions"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), index=True)
    household_id: Mapped[str] = mapped_column(ForeignKey("households.id"), index=True)
    statement_date: Mapped[date] = mapped_column(Date)
    statement_balance: Mapped[Decimal] = mapped_column(Numeric(19, 4))
    status: Mapped[str] = mapped_column(String(12), default="open", server_default="open")
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_by_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class TransferGroup(Base):
    __tablename__ = "transfer_groups"
    __table_args__ = (UniqueConstraint("household_id", "client_id", name="uq_transfer_groups_household_client_id"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    household_id: Mapped[str] = mapped_column(ForeignKey("households.id"), index=True)
    client_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_by_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Attachment(Base):
    __tablename__ = "attachments"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    transaction_id: Mapped[str] = mapped_column(ForeignKey("transactions.id"), index=True)
    household_id: Mapped[str] = mapped_column(ForeignKey("households.id"), index=True)
    filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(120))
    size_bytes: Mapped[int] = mapped_column()
    storage_path: Mapped[str] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class TransactionEditEvent(Base):
    __tablename__ = "transaction_edit_events"
    __table_args__ = (
        ForeignKeyConstraint(["transaction_id"], ["transactions.id"], name="fk_transaction_edit_events_transaction"),
        ForeignKeyConstraint(["edited_by_id"], ["users.id"], name="fk_transaction_edit_events_editor"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    transaction_id: Mapped[str] = mapped_column(String(32), index=True)
    edited_by_id: Mapped[str] = mapped_column(String(32))
    before_snapshot: Mapped[dict] = mapped_column(JSON)
    after_snapshot: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
