import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def new_id() -> str:
    return uuid.uuid4().hex


class Household(Base):
    __tablename__ = "households"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(120))
    currency_code: Mapped[str] = mapped_column(String(3), default="MXN")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    members: Mapped[list["User"]] = relationship(back_populates="household")
    accounts: Mapped[list["Account"]] = relationship(back_populates="household")
    categories: Mapped[list["Category"]] = relationship(back_populates="household")


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    name: Mapped[str] = mapped_column(String(120))
    household_id: Mapped[str | None] = mapped_column(
        ForeignKey("households.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    household: Mapped[Household | None] = relationship(back_populates="members")


class Invitation(Base):
    __tablename__ = "invitations"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    household_id: Mapped[str] = mapped_column(ForeignKey("households.id"))
    token: Mapped[str] = mapped_column(String(64), unique=True, default=new_id)
    created_by_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Account(Base):
    """Cuenta financiera. El saldo se calcula dinámicamente:
    opening_balance + suma(ingresos) - suma(gastos)."""

    __tablename__ = "accounts"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    household_id: Mapped[str] = mapped_column(ForeignKey("households.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    # cash | debit | credit | savings
    kind: Mapped[str] = mapped_column(String(20))
    opening_balance: Mapped[float] = mapped_column(Numeric(19, 4), default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    household: Mapped[Household] = relationship(back_populates="accounts")


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    household_id: Mapped[str] = mapped_column(ForeignKey("households.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    icon: Mapped[str] = mapped_column(String(60))  # nombre de icono Lucide
    color: Mapped[str] = mapped_column(String(7))  # hex, ej. "#30b0c7"
    type: Mapped[str] = mapped_column(String(10))  # expense | income
    active: Mapped[bool] = mapped_column(default=True)

    household: Mapped[Household] = relationship(back_populates="categories")


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    household_id: Mapped[str] = mapped_column(ForeignKey("households.id"), index=True)
    type: Mapped[str] = mapped_column(String(10))  # expense | income
    amount: Mapped[float] = mapped_column(Numeric(19, 4))
    category_id: Mapped[str] = mapped_column(ForeignKey("categories.id"))
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), index=True)
    member_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    date: Mapped[date] = mapped_column(Date, index=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    attachments: Mapped[list["Attachment"]] = relationship(lazy="selectin")


class Attachment(Base):
    __tablename__ = "attachments"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    transaction_id: Mapped[str] = mapped_column(
        ForeignKey("transactions.id"), index=True
    )
    household_id: Mapped[str] = mapped_column(ForeignKey("households.id"), index=True)
    filename: Mapped[str] = mapped_column(String(255))  # nombre original
    content_type: Mapped[str] = mapped_column(String(120))
    size_bytes: Mapped[int] = mapped_column()
    storage_path: Mapped[str] = mapped_column(String(500))  # ruta en disco
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class RecurringRule(Base):
    """Fase 2: esquema preparado, sin endpoints todavía."""

    __tablename__ = "recurring_rules"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    household_id: Mapped[str] = mapped_column(ForeignKey("households.id"), index=True)
    type: Mapped[str] = mapped_column(String(10))  # expense | income
    amount: Mapped[float] = mapped_column(Numeric(19, 4))
    category_id: Mapped[str] = mapped_column(ForeignKey("categories.id"))
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"))
    frequency: Mapped[str] = mapped_column(String(10))  # weekly | monthly
    next_run_date: Mapped[date] = mapped_column(Date)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(default=True)
