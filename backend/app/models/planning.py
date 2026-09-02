from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, CheckConstraint, ForeignKey, Index, JSON, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.identity import new_id


class RecurringRule(Base):
    __tablename__ = "recurring_rules"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    household_id: Mapped[str] = mapped_column(ForeignKey("households.id"), index=True)
    type: Mapped[str] = mapped_column(String(10))
    amount: Mapped[Decimal] = mapped_column(Numeric(19, 4))
    category_id: Mapped[str] = mapped_column(ForeignKey("categories.id"))
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"))
    created_by_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    frequency: Mapped[str] = mapped_column(String(10))
    next_run_date: Mapped[date] = mapped_column(Date)
    anchor_day: Mapped[int | None] = mapped_column(nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(default=True)


class Budget(Base):
    __tablename__ = "budgets"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    household_id: Mapped[str] = mapped_column(ForeignKey("households.id"), index=True)
    category_id: Mapped[str] = mapped_column(ForeignKey("categories.id"))
    amount: Mapped[Decimal] = mapped_column(Numeric(19, 4))
    month: Mapped[date | None] = mapped_column(Date, nullable=True)
    rollover: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("household_id", "category_id", "month"),
        Index("uq_budgets_household_category_global", "household_id", "category_id", unique=True, postgresql_where=month.is_(None), sqlite_where=month.is_(None)),
    )


class SavingsGoal(Base):
    __tablename__ = "savings_goals"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    household_id: Mapped[str] = mapped_column(ForeignKey("households.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    target_amount: Mapped[Decimal] = mapped_column(Numeric(19, 4))
    current_amount: Mapped[Decimal] = mapped_column(Numeric(19, 4), default=0)
    target_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    account_id: Mapped[str | None] = mapped_column(ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True, index=True)
    icon: Mapped[str] = mapped_column(String(60), default="piggy-bank")
    color: Mapped[str] = mapped_column(String(7), default="#30b0c7")
    archived: Mapped[bool] = mapped_column(default=False)
    # The plan is purely advisory: pausing it never changes the manual balance.
    plan_paused: Mapped[bool] = mapped_column(default=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class Alert(Base):
    __tablename__ = "alerts"
    __table_args__ = (UniqueConstraint("household_id", "dedupe_key", name="uq_alerts_household_dedupe_key"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    household_id: Mapped[str] = mapped_column(ForeignKey("households.id"), index=True)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    kind: Mapped[str] = mapped_column(String(40))
    message: Mapped[str] = mapped_column(String(300))
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    dedupe_key: Mapped[str] = mapped_column(String(180))
    read_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class InstalmentPlan(Base):
    """Months-without-interest plan for a card purchase.

    Advisory like goal plans: it never creates ledger movements. The
    schedule is derived from `first_due_date` (anchor-day walk, no stored
    rows); `paid_count` advances by explicit user action only.
    """

    __tablename__ = "instalment_plans"
    __table_args__ = (
        UniqueConstraint("household_id", "source_transaction_id", name="uq_instalment_plans_household_source"),
        CheckConstraint("months >= 2 AND months <= 48", name="ck_instalment_plans_months"),
        CheckConstraint("status IN ('active', 'paused', 'completed', 'cancelled')", name="ck_instalment_plans_status"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    household_id: Mapped[str] = mapped_column(ForeignKey("households.id"), index=True)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), index=True)
    source_transaction_id: Mapped[str] = mapped_column(ForeignKey("transactions.id"))
    months: Mapped[int] = mapped_column()
    total_amount: Mapped[Decimal] = mapped_column(Numeric(19, 4))
    monthly_amount: Mapped[Decimal] = mapped_column(Numeric(19, 4))
    first_due_date: Mapped[date] = mapped_column(Date)
    paid_count: Mapped[int] = mapped_column(default=0, server_default="0")
    status: Mapped[str] = mapped_column(String(12), default="active", server_default="active")
    created_by_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
