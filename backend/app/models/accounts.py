from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, ForeignKeyConstraint, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.identity import new_id


class Account(Base):
    """Financial account; its balance is derived from ledger entries."""

    __tablename__ = "accounts"
    __table_args__ = (
        UniqueConstraint("id", "household_id", name="uq_accounts_id_household_id"),
        ForeignKeyConstraint(["owner_id", "household_id"], ["users.id", "users.household_id"], name="fk_accounts_owner_membership"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    household_id: Mapped[str] = mapped_column(ForeignKey("households.id"), index=True)
    owner_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    kind: Mapped[str] = mapped_column(String(20))
    opening_balance: Mapped[float] = mapped_column(Numeric(19, 4), default=0)
    bank: Mapped[str | None] = mapped_column(String(60), nullable=True)
    card_brand: Mapped[str | None] = mapped_column(String(10), nullable=True)
    last_four: Mapped[str | None] = mapped_column(String(4), nullable=True)
    statement_day: Mapped[int | None] = mapped_column(nullable=True)
    payment_due_days: Mapped[int | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    household: Mapped["Household"] = relationship(back_populates="accounts")
