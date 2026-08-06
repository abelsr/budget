import uuid
from datetime import date, datetime

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def new_id() -> str:
    return uuid.uuid4().hex


class Household(Base):
    __tablename__ = "households"
    __table_args__ = (
        ForeignKeyConstraint(
            ["owner_id", "id"],
            ["users.id", "users.household_id"],
            name="fk_households_owner_membership",
            deferrable=True,
            initially="DEFERRED",
        ),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(120))
    currency_code: Mapped[str] = mapped_column(String(3), default="MXN")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    # Se guarda como columna, sin relación ORM, para evitar ambigüedad con
    # User.household_id, que representa la membresía. NULL solo conserva un
    # hogar legado sin miembros; los hogares nuevos siempre reciben propietario.
    owner_id: Mapped[str | None] = mapped_column(String(32), nullable=True)

    members: Mapped[list["User"]] = relationship(
        back_populates="household", foreign_keys="User.household_id"
    )
    accounts: Mapped[list["Account"]] = relationship(back_populates="household")
    categories: Mapped[list["Category"]] = relationship(back_populates="household")


class User(Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("id", "household_id", name="uq_users_id_household_id"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    name: Mapped[str] = mapped_column(String(120))
    sex: Mapped[str | None] = mapped_column(String(20), nullable=True)
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    avatar_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    avatar_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    household_id: Mapped[str | None] = mapped_column(
        ForeignKey("households.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    # NULL = el wizard inicial está pendiente. Vive en User (no en Household)
    # porque es una experiencia de quien se registra creando hogar nuevo; quien
    # entra por invitación se marca como completado al registrarse.
    onboarding_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )

    household: Mapped[Household | None] = relationship(
        back_populates="members", foreign_keys=[household_id]
    )


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
    # Datos de tarjeta opcionales (banco + últimos 4 dígitos + emisor): si se
    # definen, el widget de la cuenta se dibuja como tarjeta de wallet
    # (docs/roadmap/18-features-y-uiux-propuestas.md B1). Solo se guardan los
    # últimos 4 dígitos — nunca el número completo, no es una necesidad PCI.
    bank: Mapped[str | None] = mapped_column(String(60), nullable=True)
    # visa | mastercard | amex | other
    card_brand: Mapped[str | None] = mapped_column(String(10), nullable=True)
    last_four: Mapped[str | None] = mapped_column(String(4), nullable=True)
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
    __table_args__ = (
        Index("ix_transactions_household_date", "household_id", "date"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    household_id: Mapped[str] = mapped_column(ForeignKey("households.id"), index=True)
    type: Mapped[str] = mapped_column(String(10))  # expense | income
    amount: Mapped[float] = mapped_column(Numeric(19, 4))
    category_id: Mapped[str] = mapped_column(ForeignKey("categories.id"))
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), index=True)
    # Nombre histórico de API/DB: es el autor inmutable autenticado del movimiento.
    member_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    date: Mapped[date] = mapped_column(Date, index=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    # NULL = capturada a mano. Si viene de una regla recurrente guarda cuál,
    # para el badge y la trazabilidad. Borrar la regla la deja en NULL: la
    # transacción sobrevive (ya es dinero que se movió), pierde la etiqueta.
    recurring_rule_id: Mapped[str | None] = mapped_column(
        ForeignKey("recurring_rules.id"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    attachments: Mapped[list["Attachment"]] = relationship(lazy="selectin")
    # La autoría no depende de que la persona siga perteneciendo al hogar.
    author: Mapped[User] = relationship(foreign_keys=[member_id], lazy="selectin")


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
    """Plantilla de un movimiento que se repite (renta, sueldo, suscripción).

    Las transacciones se materializan de forma lazy al leer, no con un
    scheduler: en self-hosted no hay cron garantizado (ver
    `app.services.recurring`)."""

    __tablename__ = "recurring_rules"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    household_id: Mapped[str] = mapped_column(ForeignKey("households.id"), index=True)
    type: Mapped[str] = mapped_column(String(10))  # expense | income
    amount: Mapped[float] = mapped_column(Numeric(19, 4))
    category_id: Mapped[str] = mapped_column(ForeignKey("categories.id"))
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"))
    # Autor de la regla. Las transacciones que genera se le atribuyen: nadie
    # las captura, y achacárselas a quien casualmente abrió la app haría que el
    # mismo gasto cambiara de miembro según quién entrara primero.
    created_by_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    frequency: Mapped[str] = mapped_column(String(10))  # weekly | monthly
    next_run_date: Mapped[date] = mapped_column(Date)
    # Día del mes que la regla "quiere" (solo mensual; NULL en semanal). Sin él
    # una regla del 31 se clavaría en 28 al pasar por febrero: next_run_date
    # guarda la fecha ya recortada y el mes siguiente partiría de ahí.
    anchor_day: Mapped[int | None] = mapped_column(nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(default=True)


class Budget(Base):
    """Límite de gasto por categoría. Global (no por mes): se define una vez
    y el gasto de cada mes se recalcula en /budgets/status contra las
    transacciones de ese periodo, sin recrear el presupuesto."""

    __tablename__ = "budgets"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    household_id: Mapped[str] = mapped_column(ForeignKey("households.id"), index=True)
    category_id: Mapped[str] = mapped_column(ForeignKey("categories.id"))
    amount: Mapped[float] = mapped_column(Numeric(19, 4))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (UniqueConstraint("household_id", "category_id"),)
