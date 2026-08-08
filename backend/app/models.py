import uuid
from datetime import date, datetime

from sqlalchemy import (
    Date,
    DateTime,
    CheckConstraint,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    JSON,
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
    # Kept false until an email delivery/verification flow is deliberately added.
    email_verified: Mapped[bool] = mapped_column(default=False, server_default="false")
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

    __table_args__ = (
        UniqueConstraint("id", "household_id", name="uq_accounts_id_household_id"),
        ForeignKeyConstraint(
            ["owner_id", "household_id"],
            ["users.id", "users.household_id"],
            name="fk_accounts_owner_membership",
        ),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    household_id: Mapped[str] = mapped_column(ForeignKey("households.id"), index=True)
    # NULL = shared. A non-null value is constrained to a current household member.
    owner_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
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
    # Tombstones retain private transaction references after a peer deletes the
    # shared category, without exposing it again in category management.
    deleted: Mapped[bool] = mapped_column(default=False)

    household: Mapped[Household] = relationship(back_populates="categories")


class MerchantRule(Base):
    """Household-owned normalized merchant pattern assigned to one category."""

    __tablename__ = "merchant_rules"
    __table_args__ = (UniqueConstraint("household_id", "match_text", name="uq_merchant_rules_household_match_text"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    household_id: Mapped[str] = mapped_column(ForeignKey("households.id"), index=True)
    pattern: Mapped[str] = mapped_column(String(120))
    match_text: Mapped[str] = mapped_column(String(120))
    category_id: Mapped[str] = mapped_column(ForeignKey("categories.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    category: Mapped[Category] = relationship(lazy="joined")


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        Index("ix_transactions_household_date", "household_id", "date"),
        UniqueConstraint("household_id", "client_id", name="uq_transactions_household_client_id"),
        UniqueConstraint("id", "import_batch_id", name="uq_transactions_id_import_batch_id"),
        ForeignKeyConstraint(
            ["import_batch_id", "household_id", "account_id"],
            [
                "import_batches.id",
                "import_batches.household_id",
                "import_batches.account_id",
            ],
            name="fk_transactions_import_batch_scope",
        ),
        CheckConstraint(
            "(type = 'transfer' AND category_id IS NULL AND transfer_group_id IS NOT NULL "
            "AND transfer_direction IN ('outflow', 'inflow')) OR "
            "(type IN ('expense', 'income') AND category_id IS NOT NULL "
            "AND transfer_group_id IS NULL AND transfer_direction IS NULL)",
            name="ck_transactions_transfer_shape",
        ),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    household_id: Mapped[str] = mapped_column(ForeignKey("households.id"), index=True)
    # Device-generated UUID used to make offline creation retries idempotent.
    client_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    type: Mapped[str] = mapped_column(String(10))  # expense | income | transfer
    amount: Mapped[float] = mapped_column(Numeric(19, 4))
    category_id: Mapped[str | None] = mapped_column(ForeignKey("categories.id"), nullable=True)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), index=True)
    transfer_group_id: Mapped[str | None] = mapped_column(
        ForeignKey("transfer_groups.id"), nullable=True, index=True
    )
    # Transfer amounts remain positive; this direction supplies their balance effect.
    transfer_direction: Mapped[str | None] = mapped_column(String(10), nullable=True)
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
    # Every CSV-created transaction keeps a direct link to its import attempt.
    import_batch_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    delete_reason: Mapped[str | None] = mapped_column(String(30), nullable=True)
    # A movement can be selected only once, in the reconciliation that cleared it.
    reconciliation_status: Mapped[str] = mapped_column(String(12), default="pending", server_default="pending")
    reconciliation_session_id: Mapped[str | None] = mapped_column(
        ForeignKey("reconciliation_sessions.id"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    attachments: Mapped[list["Attachment"]] = relationship(lazy="selectin")
    # La autoría no depende de que la persona siga perteneciendo al hogar.
    author: Mapped[User] = relationship(foreign_keys=[member_id], lazy="selectin")


class ReconciliationSession(Base):
    __tablename__ = "reconciliation_sessions"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), index=True)
    household_id: Mapped[str] = mapped_column(ForeignKey("households.id"), index=True)
    statement_date: Mapped[date] = mapped_column(Date)
    statement_balance: Mapped[float] = mapped_column(Numeric(19, 4))
    # open | completed | stale
    status: Mapped[str] = mapped_column(String(12), default="open", server_default="open")
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_by_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class TransferGroup(Base):
    __tablename__ = "transfer_groups"
    __table_args__ = (
        UniqueConstraint("household_id", "client_id", name="uq_transfer_groups_household_client_id"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    household_id: Mapped[str] = mapped_column(ForeignKey("households.id"), index=True)
    # One idempotency key represents the whole two-row transfer, not either side.
    client_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_by_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


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


class SavingsGoal(Base):
    """A manual household savings target. Contributions do not create transactions."""

    __tablename__ = "savings_goals"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    household_id: Mapped[str] = mapped_column(ForeignKey("households.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    target_amount: Mapped[float] = mapped_column(Numeric(19, 4))
    current_amount: Mapped[float] = mapped_column(Numeric(19, 4), default=0)
    target_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    account_id: Mapped[str | None] = mapped_column(
        ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True, index=True
    )
    icon: Mapped[str] = mapped_column(String(60), default="piggy-bank")
    color: Mapped[str] = mapped_column(String(7), default="#30b0c7")
    archived: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class ImportBatch(Base):
    __tablename__ = "import_batches"
    __table_args__ = (
        UniqueConstraint(
            "id",
            "household_id",
            "account_id",
            name="uq_import_batches_id_household_account",
        ),
        ForeignKeyConstraint(
            ["account_id", "household_id"],
            ["accounts.id", "accounts.household_id"],
            name="fk_import_batches_account_household",
        ),
        ForeignKeyConstraint(
            ["created_by_id", "household_id"],
            ["users.id", "users.household_id"],
            name="fk_import_batches_creator_membership",
        ),
        ForeignKeyConstraint(
            ["household_id"],
            ["households.id"],
            name="fk_import_batches_household",
        ),
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
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class ImportRow(Base):
    __tablename__ = "import_rows"
    __table_args__ = (
        UniqueConstraint("batch_id", "source_position", name="uq_import_rows_batch_position"),
        UniqueConstraint(
            "id",
            "batch_id",
            "transaction_id",
            name="uq_import_rows_id_batch_transaction",
        ),
        ForeignKeyConstraint(
            ["transaction_id", "batch_id"],
            ["transactions.id", "transactions.import_batch_id"],
            name="fk_import_rows_transaction_batch",
        ),
        ForeignKeyConstraint(
            ["batch_id"],
            ["import_batches.id"],
            name="fk_import_rows_batch",
        ),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    batch_id: Mapped[str] = mapped_column(String(32), index=True)
    source_position: Mapped[int] = mapped_column()
    source_snapshot: Mapped[dict] = mapped_column(JSON)
    transaction_baseline: Mapped[dict] = mapped_column(JSON)
    # Preview duplicate signals are advisory, but retained with each attempt for audit.
    advisory_reasons: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(20))
    transaction_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class ImportFingerprint(Base):
    __tablename__ = "import_fingerprints"
    __table_args__ = (
        UniqueConstraint(
            "household_id",
            "account_id",
            "fingerprint",
            name="uq_import_fingerprints_household_account_fingerprint",
        ),
        ForeignKeyConstraint(
            ["batch_id", "household_id", "account_id"],
            [
                "import_batches.id",
                "import_batches.household_id",
                "import_batches.account_id",
            ],
            name="fk_import_fingerprints_batch_scope",
        ),
        ForeignKeyConstraint(
            ["import_row_id", "batch_id", "transaction_id"],
            [
                "import_rows.id",
                "import_rows.batch_id",
                "import_rows.transaction_id",
            ],
            name="fk_import_fingerprints_row_transaction",
        ),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    batch_id: Mapped[str] = mapped_column(String(32), index=True)
    household_id: Mapped[str] = mapped_column(String(32), index=True)
    account_id: Mapped[str] = mapped_column(String(32), index=True)
    fingerprint: Mapped[str] = mapped_column(String(64))
    import_row_id: Mapped[str] = mapped_column(String(32), index=True)
    transaction_id: Mapped[str] = mapped_column(String(32), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class TransactionEditEvent(Base):
    __tablename__ = "transaction_edit_events"
    __table_args__ = (
        ForeignKeyConstraint(
            ["transaction_id"],
            ["transactions.id"],
            name="fk_transaction_edit_events_transaction",
        ),
        ForeignKeyConstraint(
            ["edited_by_id"],
            ["users.id"],
            name="fk_transaction_edit_events_editor",
        ),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    transaction_id: Mapped[str] = mapped_column(String(32), index=True)
    edited_by_id: Mapped[str] = mapped_column(String(32))
    before_snapshot: Mapped[dict] = mapped_column(JSON)
    after_snapshot: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
