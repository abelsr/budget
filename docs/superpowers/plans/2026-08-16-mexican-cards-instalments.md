# Mexican Cards and Instalments Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers/executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement roadmap doc 23 — card cycle dates (statement day + days-to-payment-due), MSI instalment plans, and their integration into the cash-flow forecast and in-app alerts.

**Architecture:** Card cycle dates are derived (never stored) from two new nullable columns on `accounts`. MSI plans live in a new `instalment_plans` table whose month-by-month schedule is derived from `first_due_date` with the existing anchor-day `advance()` walk — no stored schedule rows, no ledger movements (advisory, like goal plans). Paying a card creates a standard cash→card `transfer_groups` pair. Forecast gains two advisory `upcoming` event sources; alerts gain two kinds on the lazy idempotent pass.

**Tech Stack:** FastAPI, SQLAlchemy 2, Alembic (PostgreSQL-only runtime; SQLite in-memory for unit tests), pytest; React 19 + Vite, TanStack Query, Tailwind. Spec: `docs/roadmap/23-tarjetas-mx-e-instalados.md`.

**Conventions (repo):** backend tests in `backend/tests/` (SQLite `create_all` via `conftest.py` fixtures `session`/`client`); camelCase schemas via `_CamelModel` (`pydantic.alias_generators.to_camel`); read endpoints call `materialize_due` first; Spanish user-facing copy; English code comments and commit messages (imperative).

---

## Chunk 1: Schema, models, date helpers

### Task 1: Alembic migration

**Files:**
- Create: `backend/alembic/versions/a3f5b7c9d1e2_tarjetas_mx_e_instalados.py` (revises `c7d8e9f0a1b2`, the current head)

- [ ] **Step 1: Write the migration**

```python
"""cuentas de tarjeta y planes de instalados

Revision ID: a3f5b7c9d1e2
Revises: c7d8e9f0a1b2
Create Date: 2026-08-16
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a3f5b7c9d1e2"
down_revision: str | None = "c7d8e9f0a1b2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("accounts", sa.Column("statement_day", sa.Integer(), nullable=True))
    op.add_column("accounts", sa.Column("payment_due_days", sa.Integer(), nullable=True))
    op.create_check_constraint(
        "ck_accounts_statement_day", "accounts", "statement_day IS NULL OR (statement_day >= 1 AND statement_day <= 28)"
    )
    op.create_check_constraint(
        "ck_accounts_payment_due_days", "accounts", "payment_due_days IS NULL OR (payment_due_days >= 1 AND payment_due_days <= 60)"
    )
    op.create_table(
        "instalment_plans",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column("household_id", sa.String(length=32), sa.ForeignKey("households.id"), nullable=False),
        sa.Column("account_id", sa.String(length=32), sa.ForeignKey("accounts.id"), nullable=False),
        sa.Column("source_transaction_id", sa.String(length=32), sa.ForeignKey("transactions.id"), nullable=False),
        sa.Column("months", sa.Integer(), nullable=False),
        sa.Column("total_amount", sa.Numeric(precision=19, scale=4), nullable=False),
        sa.Column("monthly_amount", sa.Numeric(precision=19, scale=4), nullable=False),
        sa.Column("first_due_date", sa.Date(), nullable=False),
        sa.Column("paid_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=12), nullable=False, server_default="active"),
        sa.Column("created_by_id", sa.String(length=32), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("household_id", "source_transaction_id", name="uq_instalment_plans_household_source"),
        sa.CheckConstraint("months >= 2 AND months <= 48", name="ck_instalment_plans_months"),
        sa.CheckConstraint("status IN ('active', 'paused', 'completed', 'cancelled')", name="ck_instalment_plans_status"),
    )
    op.create_index("ix_instalment_plans_household_id", "instalment_plans", ["household_id"])
    op.create_index("ix_instalment_plans_account_id", "instalment_plans", ["account_id"])


def downgrade() -> None:
    op.drop_index("ix_instalment_plans_account_id", table_name="instalment_plans")
    op.drop_index("ix_instalment_plans_household_id", table_name="instalment_plans")
    op.drop_table("instalment_plans")
    op.drop_constraint("ck_accounts_payment_due_days", "accounts", type_="check")
    op.drop_constraint("ck_accounts_statement_day", "accounts", type_="check")
    op.drop_column("accounts", "payment_due_days")
    op.drop_column("accounts", "statement_day")
```

- [ ] **Step 2: Verify model/migration drift is detected**

Run: `cd backend && uv run pytest tests/test_migrations.py -q` (Postgres needed; skipped locally is fine) and `uv run alembic heads` → expected: single head `a3f5b7c9d1e2`. Without the model (next task) `alembic check` would report drift — that is the intended failing state.

- [ ] **Step 3: Commit**

```bash
git add backend/alembic/versions/a3f5b7c9d1e2_tarjetas_mx_e_instalados.py
git commit -m "Add migration for card cycle dates and instalment plans"
```

### Task 2: Models

**Files:**
- Modify: `backend/app/models/accounts.py`
- Modify: `backend/app/models/planning.py`
- Modify: `backend/app/models/__init__.py`

- [ ] **Step 1: Add account columns**

In `app/models/accounts.py`, after `last_four`:

```python
    statement_day: Mapped[int | None] = mapped_column(nullable=True)
    payment_due_days: Mapped[int | None] = mapped_column(nullable=True)
```

- [ ] **Step 2: Add `InstalmentPlan`**

In `app/models/planning.py`, after `Alert`:

```python
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
    total_amount: Mapped[float] = mapped_column(Numeric(19, 4))
    monthly_amount: Mapped[float] = mapped_column(Numeric(19, 4))
    first_due_date: Mapped[date] = mapped_column(Date)
    paid_count: Mapped[int] = mapped_column(default=0, server_default="0")
    status: Mapped[str] = mapped_column(String(12), default="active", server_default="active")
    created_by_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
```

`planning.py` already imports `CheckConstraint`? If not, add it to the sqlalchemy import line.

- [ ] **Step 3: Re-export**

In `app/models/__init__.py`, add `InstalmentPlan` to the `app.models.planning` import (alphabetical).

- [ ] **Step 4: Verify**

Run: `cd backend && uv run pytest -q` → expected: all pass (new columns/table created by `create_all`; nothing references them yet).

- [ ] **Step 5: Commit**

```bash
git add backend/app/models/
git commit -m "Add card cycle fields and InstalmentPlan model"
```

### Task 3: Card calendar helpers (pure, TDD)

**Files:**
- Create: `backend/app/services/card_calendar.py`
- Test: `backend/tests/test_card_calendar.py`

- [ ] **Step 1: Write the failing tests**

```python
from datetime import date

import pytest

from app.services.card_calendar import (
    instalment_schedule,
    last_statement_date,
    next_statement_date,
    payment_due_date,
)


class _Plan:
    """Minimal stand-in: the schedule helpers take only these attributes."""

    def __init__(self, first_due_date, months, monthly_amount, total_amount, paid_count=0, status="active"):
        self.first_due_date = first_due_date
        self.months = months
        self.monthly_amount = monthly_amount
        self.total_amount = total_amount
        self.paid_count = paid_count
        self.status = status


def test_next_statement_date_strictly_after():
    assert next_statement_date(15, date(2026, 8, 15)) == date(2026, 9, 15)
    assert next_statement_date(15, date(2026, 8, 16)) == date(2026, 9, 15)
    assert next_statement_date(15, date(2026, 8, 14)) == date(2026, 8, 15)


def test_last_statement_date_strictly_before():
    assert last_statement_date(15, date(2026, 8, 15)) == date(2026, 7, 15)
    assert last_statement_date(15, date(2026, 8, 16)) == date(2026, 8, 15)


def test_statement_day_crosses_year():
    assert next_statement_date(28, date(2026, 12, 31)) == date(2027, 1, 28)
    assert last_statement_date(1, date(2026, 1, 1)) == date(2025, 12, 1)


def test_payment_due_crosses_month():
    assert payment_due_date(date(2026, 8, 15), 20) == date(2026, 9, 4)
    assert payment_due_date(date(2026, 12, 15), 20) == date(2027, 1, 4)


def test_schedule_anchor_day_crosses_february():
    plan = _Plan(date(2027, 1, 31), 3, 100.0, 300.0)
    dates = [d for d, _ in instalment_schedule(plan)]
    assert dates == [date(2027, 1, 31), date(2027, 2, 28), date(2027, 3, 31)]


def test_schedule_anchor_day_leap_year():
    plan = _Plan(date(2028, 1, 31), 3, 100.0, 300.0)
    dates = [d for d, _ in instalment_schedule(plan)]
    assert dates == [date(2028, 1, 31), date(2028, 2, 29), date(2028, 3, 31)]


def test_schedule_last_installment_absorbs_rounding():
    plan = _Plan(date(2026, 9, 10), 6, 850.1667, 5101.0)
    schedule = instalment_schedule(plan)
    assert len(schedule) == 6
    assert [round(a, 4) for _, a in schedule[:5]] == [850.1667] * 5
    assert round(schedule[5][1], 4) == round(5101.0 - 5 * 850.1667, 4)  # 850.1665
    assert round(sum(a for _, a in schedule), 4) == 5101.0
```

- [ ] **Step 2: Run to verify failure**

Run: `cd backend && uv run pytest tests/test_card_calendar.py -q`
Expected: FAIL — `ModuleNotFoundError: app.services.card_calendar`

- [ ] **Step 3: Implement `app/services/card_calendar.py`**

```python
"""Pure date math for card cycles and MSI instalment schedules.

Shared by the account API, the forecast, and the alerts so the three can
never drift. Dates are derived, never stored.
"""

from datetime import date, timedelta

from app.services.recurring import advance


def next_statement_date(statement_day: int, after: date) -> date:
    """First day-`statement_day` occurrence strictly after `after`."""
    candidate = _place_day(after.year, after.month, statement_day)
    if candidate <= after:
        year = candidate.year + 1 if candidate.month == 12 else candidate.year
        month = 1 if candidate.month == 12 else candidate.month + 1
        candidate = _place_day(year, month, statement_day)
    return candidate


def last_statement_date(statement_day: int, before: date) -> date:
    """Last day-`statement_day` occurrence strictly before `before`."""
    candidate = _place_day(before.year, before.month, statement_day)
    if candidate >= before:
        year = candidate.year - 1 if candidate.month == 1 else candidate.year
        month = 12 if candidate.month == 1 else candidate.month - 1
        candidate = _place_day(year, month, statement_day)
    return candidate


def _place_day(year: int, month: int, day: int) -> date:
    # statement_day is constrained to 1..28, so no month-length clamp is
    # needed here (unlike anchor days, which may be 29-31).
    return date(year, month, day)


def payment_due_date(statement: date, payment_due_days: int) -> date:
    return statement + timedelta(days=payment_due_days)


def instalment_schedule(plan) -> tuple[tuple[date, float], ...]:
    """Derived (due date, amount) pairs for every instalment.

    Walks `advance()` monthly from `first_due_date` keeping the anchor day,
    so Jan 31 -> Feb 28/29 -> Mar 31. The last instalment absorbs the
    rounding remainder so the instalments sum exactly to `total_amount`.
    """
    items: list[tuple[date, float]] = []
    current = plan.first_due_date
    for index in range(plan.months):
        amount = (
            round(float(plan.total_amount) - index * float(plan.monthly_amount), 4)
            if index == plan.months - 1
            else float(plan.monthly_amount)
        )
        items.append((current, amount))
        current = advance(current, "monthly", anchor_day=plan.first_due_date.day)
    return tuple(items)


def next_unpaid_due(plan) -> tuple[date, float] | None:
    """The next (due date, amount) still unpaid, or None when completed."""
    if plan.paid_count >= plan.months:
        return None
    return instalment_schedule(plan)[plan.paid_count]
```

- [ ] **Step 4: Run to verify pass**

Run: `cd backend && uv run pytest tests/test_card_calendar.py -q` → Expected: PASS (7 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/card_calendar.py backend/tests/test_card_calendar.py
git commit -m "Add card calendar date helpers"
```

---

## Chunk 2: Account cycle fields

### Task 4: Account schemas and endpoints

**Files:**
- Modify: `backend/app/schemas/accounts.py`
- Modify: `backend/app/api/routes/accounts.py`
- Test: `backend/tests/test_card_cycle.py` (new)

- [ ] **Step 1: Write the failing tests**

Follow the existing fixture style in `tests/test_personal_accounts.py` (register → household → accounts). Key cases:

```python
def test_credit_account_accepts_cycle_and_derives_dates(client, auth):
    # POST /api/accounts {name, kind: "credit", statementDay: 15, paymentDueDays: 20}
    # -> 201, out has statementDay 15, paymentDueDays 20,
    #    nextStatementDate/nextPaymentDueDate/lastStatementDate all non-null
    #    and consistent (next > today >= last; due = next + 20d)

def test_non_credit_account_rejects_cycle(client, auth):
    # kind "cash" with statementDay -> 422

def test_patch_kind_to_cash_requires_clearing_cycle(client, auth):
    # credit with cycle set; PATCH {kind: "cash"} -> 422
    # PATCH {kind: "cash", statementDay: null, paymentDueDays: null} -> 200, dates null

def test_patch_cycle_to_credit_only(client, auth):
    # cash account; PATCH {statementDay: 15} -> 422
    # PATCH {kind: "credit", statementDay: 15, paymentDueDays: 20} -> 200
```

- [ ] **Step 2: Run to verify failure**

Run: `cd backend && uv run pytest tests/test_card_cycle.py -q` → Expected: FAIL (422/500 or field ignored)

- [ ] **Step 3: Schemas**

In `app/schemas/accounts.py`:

- `AccountCreate`: add `statement_day: int | None = Field(default=None, ge=1, le=28)` and `payment_due_days: int | None = Field(default=None, ge=1, le=60)`.
- `AccountUpdate`: add the same two fields (nullable, same bounds).
- `AccountOut`: add `statement_day: int | None`, `payment_due_days: int | None`, `next_statement_date: str | None`, `last_statement_date: str | None`, `next_payment_due_date: str | None` (ISO strings via `.isoformat()`).

- [ ] **Step 4: Endpoint wiring**

In `app/api/routes/accounts.py`:

- `_account_out(account, balance, today)`: compute derived dates with a small local helper:

```python
def _card_dates(account: Account, today: date) -> tuple[str | None, str | None, str | None]:
    """(last_statement, next_statement, next_payment_due) as ISO strings."""
    if account.kind != "credit" or account.statement_day is None or account.payment_due_days is None:
        return (None, None, None)
    from app.services.card_calendar import last_statement_date, next_statement_date, payment_due_date

    nxt = next_statement_date(account.statement_day, today)
    return (
        last_statement_date(account.statement_day, today).isoformat(),
        nxt.isoformat(),
        payment_due_date(nxt, account.payment_due_days).isoformat(),
    )
```

Pass `date.today()` from the endpoints (import `date` from `datetime`).

- `create_account`: before `db.add`, validate cycle vs kind:

```python
    if (payload.statement_day is not None or payload.payment_due_days is not None) and payload.kind != "credit":
        raise HTTPException(status_code=422, detail="Las fechas de ciclo solo aplican a cuentas de tarjeta de crédito")
```

Set the two fields on the `Account(...)` constructor.

- `update_account`: after `data = payload.model_dump(exclude_unset=True)` and the `is_personal` handling, validate:

```python
    effective_kind = data.get("kind", account.kind)
    has_cycle_request = "statement_day" in data or "payment_due_days" in data
    if has_cycle_request and effective_kind != "credit":
        raise HTTPException(status_code=422, detail="Las fechas de ciclo solo aplican a cuentas de tarjeta de crédito")
    if data.get("kind") in (None, "credit") and effective_kind != "credit":
        # kind changed away from credit with cycle still set and not cleared
        raise HTTPException(status_code=422, detail="Las fechas de ciclo solo aplican a cuentas de tarjeta de crédito")
```

(Both rules collapse to: *after this update, `kind != "credit"` implies both cycle fields must be None* — implement with one `if` over the effective post-update state.)

- [ ] **Step 5: Run tests**

Run: `cd backend && uv run pytest tests/test_card_cycle.py -q` → Expected: PASS
Run: `cd backend && uv run pytest -q` → Expected: all pass (existing account tests unaffected)

- [ ] **Step 6: Commit**

```bash
git add backend/app/schemas/accounts.py backend/app/api/routes/accounts.py backend/tests/test_card_cycle.py
git commit -m "Expose card cycle dates on account endpoints"
```

---

## Chunk 3: Instalment plan endpoints

### Task 5: Schemas

**Files:**
- Create: `backend/app/schemas/instalment_plans.py`

- [ ] **Step 1: Write the schemas**

```python
from datetime import date

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

InstalmentPlanStatus = "active"  # runtime set: active, paused, completed, cancelled


class _CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class InstalmentPlanCreate(_CamelModel):
    source_transaction_id: str
    months: int = Field(ge=2, le=48)
    first_due_date: date


class InstalmentPlanPay(_CamelModel):
    #: When set, a cash->card transfer is created for the instalment.
    source_account_id: str | None = None
    date: date | None = None


class InstalmentScheduleItem(_CamelModel):
    date: date
    amount: float
    paid: bool


class InstalmentPlanOut(_CamelModel):
    id: str
    household_id: str
    account_id: str
    account_name: str
    source_transaction_id: str
    months: int
    total_amount: float
    monthly_amount: float
    first_due_date: date
    paid_count: int
    status: str
    next_due_date: date | None
    next_due_amount: float | None
    schedule: list[InstalmentScheduleItem]
    created_at: date  # or datetime — match existing Out conventions
```

### Task 6: Service + router

**Files:**
- Create: `backend/app/services/instalment_plans.py`
- Create: `backend/app/api/routes/instalment_plans.py`
- Modify: `backend/app/main.py` (register router)
- Test: `backend/tests/test_instalment_plans.py` (new)

- [ ] **Step 1: Write the failing tests**

Setup helpers (reuse patterns from `tests/test_budgets.py` / `test_goals.py`): create a credit account (shared, with cycle optional) and an expense transaction on it via `POST /api/transactions`. Key cases:

```python
def test_create_plan_from_card_purchase(client, auth, card_account, purchase):
    # POST /api/instalment-plans {sourceTransactionId, months: 6, firstDueDate: "2026-09-30"}
    # -> 201: months 6, monthlyAmount round(5100/6,4)=850, totalAmount 5100,
    #    status active, paidCount 0, nextDueDate 2026-09-30,
    #    schedule 6 items, accountName set

def test_create_plan_rounding_remainder(client, auth, card_account, purchase_5101):
    # months 6 -> monthly 850.1667, schedule last item 850.1665, sums to 5101

def test_create_plan_guards(client, auth, ...):
    # duplicate on same purchase -> 409
    # income transaction -> 422
    # transfer -> 422
    # soft-deleted (import-reverted) purchase -> 404
    # personal card account -> 422
    # first_due_date in the past -> 422
    # other household's purchase -> 404

def test_list_and_detail(client, auth):
    # GET /api/instalment-plans -> active+paused only, household-isolated
    # GET /api/instalment-plans/{id} -> full schedule

def test_pay_marks_instalment(client, auth):
    # POST .../pay {} -> paidCount 1, nextDue advances one month (anchor day)

def test_pay_with_transfer_creates_group(client, auth, cash_account):
    # POST .../pay {sourceAccountId: cash} -> paidCount 1
    # GET /api/accounts: cash balance -X, card balance +X
    # GET /api/transactions?type=transfer (include transfers): pair exists,
    #    note mentions MSI, excluded from expense totals in GET /api/summary

def test_pay_completes_at_last_instalment(client, auth):
    # pay until paidCount == months -> status "completed", nextDueDate null

def test_pause_resume_cancel(client, auth):
    # pause -> status paused; resume -> active; cancel -> deleted (GET -> 404 or 204 DELETE)
    # pause/cancel a completed plan -> 409
```

- [ ] **Step 2: Run to verify failure**

Run: `cd backend && uv run pytest tests/test_instalment_plans.py -q` → Expected: FAIL (404 no route)

- [ ] **Step 3: Service `app/services/instalment_plans.py`**

```python
"""MSI instalment plan lifecycle. Advisory: never creates ledger movements
except the explicit cash->card transfer when the user records a payment."""

from datetime import date

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Account, InstalmentPlan, Transaction, TransferGroup
from app.services.account_access import can_operate
from app.services.card_calendar import instalment_schedule, next_unpaid_due
from app.services.reconciliation import invalidate_completed_reconciliation

ACTIVE_STATUSES = ("active", "paused")


def get_plan_or_404(db: Session, household_id: str, plan_id: str) -> InstalmentPlan:
    plan = db.get(InstalmentPlan, plan_id)
    if plan is None or plan.household_id != household_id:
        raise HTTPException(status_code=404, detail="Plan no encontrado")
    return plan


def active_plan_for(db: Session, transaction_id: str) -> InstalmentPlan | None:
    return db.scalar(
        select(InstalmentPlan).where(
            InstalmentPlan.source_transaction_id == transaction_id,
            InstalmentPlan.status.in_(ACTIVE_STATUSES),
        )
    )


def create_plan(db, *, household_id, user_id, source_transaction_id, months, first_due_date) -> InstalmentPlan:
    if db.scalar(select(InstalmentPlan.id).where(InstalmentPlan.household_id == household_id, InstalmentPlan.source_transaction_id == source_transaction_id)):
        raise HTTPException(status_code=409, detail="Esta compra ya tiene un plan de instalados")
    purchase = db.scalar(select(Transaction).where(Transaction.id == source_transaction_id, Transaction.household_id == household_id, Transaction.deleted_at.is_(None)))
    if purchase is None:
        raise HTTPException(status_code=404, detail="Movimiento no encontrado")
    if purchase.type != "expense" or purchase.account_id is None:
        raise HTTPException(status_code=422, detail="Solo una compra (gasto) en tarjeta puede tener un plan")
    account = db.get(Account, purchase.account_id)
    if account is None or account.household_id != household_id or account.kind != "credit":
        raise HTTPException(status_code=422, detail="El plan requiere una cuenta de tarjeta de crédito compartida")
    if account.owner_id is not None:
        raise HTTPException(status_code=422, detail="El plan requiere una cuenta compartida del hogar")
    if first_due_date < date.today():
        raise HTTPException(status_code=422, detail="La primera fecha de pago no puede estar en el pasado")
    total = round(float(purchase.amount), 4)
    plan = InstalmentPlan(
        household_id=household_id,
        account_id=account.id,
        source_transaction_id=purchase.id,
        months=months,
        total_amount=total,
        monthly_amount=round(total / months, 4),
        first_due_date=first_due_date,
        created_by_id=user_id,
    )
    db.add(plan)
    db.flush()
    return plan


def plan_out(plan: InstalmentPlan, account_name: str) -> dict:
    nxt = next_unpaid_due(plan)
    return {
        "id": plan.id,
        "household_id": plan.household_id,
        "account_id": plan.account_id,
        "account_name": account_name,
        "source_transaction_id": plan.source_transaction_id,
        "months": plan.months,
        "total_amount": float(plan.total_amount),
        "monthly_amount": float(plan.monthly_amount),
        "first_due_date": plan.first_due_date,
        "paid_count": plan.paid_count,
        "status": plan.status,
        "next_due_date": nxt[0] if nxt else None,
        "next_due_amount": round(nxt[1], 2) if nxt else None,
        "schedule": [
            {"date": due, "amount": round(amount, 2), "paid": index < plan.paid_count}
            for index, (due, amount) in enumerate(instalment_schedule(plan))
        ],
        "created_at": plan.created_at,
    }


def mark_paid(db: Session, plan: InstalmentPlan, *, user_id: str, source_account_id: str | None = None, payment_date: date | None = None) -> None:
    if plan.status != "active":
        raise HTTPException(status_code=409, detail=f"El plan está {plan.status}")
    if plan.paid_count >= plan.months:
        raise HTTPException(status_code=409, detail="El plan ya está completado")
    if source_account_id is not None:
        _create_payment_transfer(db, plan=plan, household_id=plan.household_id, user_id=user_id, source_account_id=source_account_id, payment_date=payment_date or date.today())
    plan.paid_count += 1
    if plan.paid_count == plan.months:
        plan.status = "completed"


def _create_payment_transfer(db, *, plan, household_id, user_id, source_account_id, payment_date) -> None:
    source = db.get(Account, source_account_id)
    card = db.get(Account, plan.account_id)
    if source is None or source.household_id != household_id or source.id == card.id:
        raise HTTPException(status_code=422, detail="Elige una cuenta de origen distinta de la tarjeta")
    if source.owner_id is not None or not can_operate(source, user_id):
        raise HTTPException(status_code=422, detail="La cuenta de origen debe ser compartida y visible")
    amount = instalment_schedule(plan)[plan.paid_count][1]
    group = TransferGroup(household_id=household_id, client_id=None, created_by_id=user_id)
    db.add(group)
    db.flush()
    outgoing = Transaction(
        household_id=household_id, type="transfer", amount=amount,
        account_id=source.id, member_id=user.id, date=payment_date,
        note=f"Instalado {plan.paid_count + 1}/{plan.months}",
        transfer_group_id=group.id, transfer_direction="outflow",
    )
    incoming = Transaction(
        household_id=household_id, type="transfer", amount=amount,
        account_id=card.id, member_id=user_id, date=payment_date,
        note=f"Instalado {plan.paid_count + 1}/{plan.months}",
        transfer_group_id=group.id, transfer_direction="inflow",
    )
    db.add_all([outgoing, incoming])
    invalidate_completed_reconciliation(db, outgoing)
    invalidate_completed_reconciliation(db, incoming)


def set_status(db: Session, plan: InstalmentPlan, status: str) -> None:
    if plan.status not in ACTIVE_STATUSES:
        raise HTTPException(status_code=409, detail=f"El plan está {plan.status}")
    plan.status = status
```

- [ ] **Step 4: Router `app/api/routes/instalment_plans.py`**

`APIRouter(prefix="/instalment-plans", tags=["instalment-plans"])`; endpoints (all sync `def`, `DbDep`/`CurrentUserDep`):

- `POST ""` (201): `InstalmentPlanCreate` → `create_plan` → commit → `plan_out`.
- `GET ""`: active+paused plans for the household, joined account name, ordered by `next_due_date` (derived) or `created_at`; list form (schedule omitted or included — include, it is small: ≤48 items).
- `GET "/{plan_id}"`: `get_plan_or_404` → full `plan_out`.
- `POST "/{plan_id}/pay"`: `InstalmentPlanPay` → `mark_paid` → commit → `plan_out`.
- `POST "/{plan_id}/pause"` / `POST "/{plan_id}/resume"`: `set_status` → commit → `plan_out`.
- `DELETE "/{plan_id}"` (204): `set_status(plan, "cancelled")` (cancel = soft, keeps history) → commit.

Register in `app/main.py` alongside the other routers.

- [ ] **Step 5: Run tests**

Run: `cd backend && uv run pytest tests/test_instalment_plans.py -q` → Expected: PASS
Run: `cd backend && uv run pytest -q` → Expected: all pass

- [ ] **Step 6: Commit**

```bash
git add backend/app/schemas/instalment_plans.py backend/app/services/instalment_plans.py backend/app/api/routes/instalment_plans.py backend/app/main.py backend/tests/test_instalment_plans.py
git commit -m "Add instalment plan endpoints"
```

### Task 7: Guards on existing endpoints

**Files:**
- Modify: `backend/app/api/routes/transactions.py` (delete + update)
- Modify: `backend/app/api/routes/accounts.py` (delete)
- Test: extend `backend/tests/test_instalment_plans.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_delete_purchase_blocked_by_active_plan(client, auth, plan):
    # DELETE /api/transactions/{purchase.id} -> 409 "plan"
    # after DELETE /api/instalment-plans/{plan.id} -> delete succeeds (204)

def test_edit_purchase_amount_blocked_by_active_plan(client, auth, plan):
    # PATCH /api/transactions/{purchase.id} {amount: 9999} -> 409
    # PATCH {note: "hola"} -> 200 (non-amount edits allowed)

def test_delete_card_account_blocked_by_active_plan(client, auth, plan, card_account, no_movements_scenario):
    # a card with no transactions except the purchase? account delete requires
    # zero movements, so use a second empty card with a plan? -> keep simple:
    # assert the guard query exists by creating a plan then attempting delete
    # on a card account that has a plan and zero other movements is impossible
    # (the purchase itself is a movement). Guard is therefore defensive:
    # verify order — movements check fires first. Document in test docstring.
```

(If the account-delete guard is unreachable because the purchase always blocks with "tiene movimientos", keep the guard anyway for the soft-deleted-purchase edge — an import-reverted purchase keeps `deleted_at` set, so the movement count... note: `has_movements` counts ALL rows including soft-deleted, so the guard is still defensive. Keep it; test with a soft-deleted purchase.)

- [ ] **Step 2: Run to verify failure** → Expected: FAIL (delete succeeds / edit succeeds today)

- [ ] **Step 3: Implement guards**

`transactions.py` `delete_transaction`, at the top (after `_get_transaction`, before the imported-row check or just after it):

```python
    from app.services.instalment_plans import active_plan_for
    if active_plan_for(db, tx.id) is not None:
        raise HTTPException(status_code=409, detail="La compra tiene un plan de instalados activo; cancela el plan primero")
```

`transactions.py` `update_transaction`, in the non-transfer branch after `data = payload.model_dump(exclude_unset=True)`:

```python
    if "amount" in data or "account_id" in data:
        from app.services.instalment_plans import active_plan_for
        if active_plan_for(db, tx.id) is not None:
            raise HTTPException(status_code=409, detail="No se puede editar el monto o la cuenta de una compra con un plan de instalados activo")
```

`accounts.py` `delete_account`, alongside the existing guards:

```python
    from app.services.instalment_plans import InstalmentPlan  # or import from app.models
    has_plans = db.scalar(select(InstalmentPlan.id).where(InstalmentPlan.account_id == account.id, InstalmentPlan.status.in_(["active", "paused"])).limit(1))
    if has_plans:
        raise HTTPException(status_code=409, detail="La cuenta tiene planes de instalados activos")
```

- [ ] **Step 4: Run tests** → Expected: PASS; full suite green.

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/routes/transactions.py backend/app/api/routes/accounts.py backend/tests/test_instalment_plans.py
git commit -m "Guard purchases, transfers of ownership, and card accounts against active plans"
```

---

## Chunk 4: Forecast and alerts integration

### Task 8: Forecast events

**Files:**
- Modify: `backend/app/services/forecast.py`
- Modify: `backend/app/schemas/forecast.py`
- Test: extend `backend/tests/test_forecast.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_card_due_event_in_upcoming(client, auth, card_account_with_cycle, negative_card_balance):
    # card balance -12000 (expenses on it), due date inside 30d window
    # GET /api/forecast -> upcoming contains {source: "card_due", type: "expense",
    #    amount: 12000, label contains card name}
    # balance series unchanged: first point balance == opening,
    #    final == opening + sum(deltas)  (existing invariant test still passes)

def test_card_due_reduced_by_scheduled_inflows(client, auth, ...):
    # a recorded transfer cash->card dated tomorrow for 5000
    # -> card_due amount 7000

def test_instalment_due_event(client, auth, plan):
    # active plan next due inside window -> upcoming {source: "instalment_due", amount: monthly}
    # paused plan -> no event

def test_no_card_events_without_cycle(client, auth, card_account_without_cycle):
    # -> no card_due events
```

- [ ] **Step 2: Run to verify failure** → Expected: FAIL (no events)

- [ ] **Step 3: Implement in `build_forecast`**

After the recurring-rules loop, before `events.sort(...)`:

```python
    # Card payment due dates and MSI instalment due dates are advisory
    # liquidity events: paying a card is a transfer that nets to zero in the
    # shared household balance, so they never enter the daily walk.
    for account in shared.values():
        if account.kind != "credit" or account.statement_day is None or account.payment_due_days is None:
            continue
        due = payment_due_date(next_statement_date(account.statement_day, as_of), account.payment_due_days)
        if not (as_of < due <= window_end):
            continue
        card_balance = account_balance(account.opening_balance, account_sums.get(account.id, {}))
        outstanding = max(0.0, -card_balance)
        scheduled = db.scalar(
            select(func.coalesce(func.sum(Transaction.amount), 0)).where(
                Transaction.account_id == account.id,
                Transaction.type == "transfer",
                Transaction.transfer_direction == "inflow",
                Transaction.deleted_at.is_(None),
                Transaction.date >= as_of,
                Transaction.date <= due,
            )
        ) or 0.0
        events.append(
            UpcomingEvent(
                date=due, type="expense", amount=round(max(0.0, outstanding - float(scheduled)), 2),
                label=f"Pago tarjeta {account.name}", source="card_due",
            )
        )

    for plan in db.scalars(select(InstalmentPlan).where(
        InstalmentPlan.household_id == household_id, InstalmentPlan.status == "active"
    )):
        nxt = next_unpaid_due(plan)
        if nxt and as_of < nxt[0] <= window_end:
            card_name = shared.get(plan.account_id)
            events.append(
                UpcomingEvent(
                    date=nxt[0], type="expense", amount=round(nxt[1], 2),
                    label=f"Instalado {plan.paid_count + 1}/{plan.months} · {card_name.name if card_name else ''}".rstrip(" ·"),
                    source="instalment_due",
                )
            )
```

Imports: `from app.services.card_calendar import next_statement_date, payment_due_date`, `from app.services.card_calendar import next_unpaid_due`, `from app.models import ... InstalmentPlan`, `from sqlalchemy import func`.

`app/schemas/forecast.py`: `ForecastUpcoming.source: Literal["transaction", "recurring", "card_due", "instalment_due"]`.

- [ ] **Step 4: Run tests** → Expected: PASS; full suite green (existing forecast invariants untouched).

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/forecast.py backend/app/schemas/forecast.py backend/tests/test_forecast.py
git commit -m "Add card due and instalment due events to the forecast"
```

### Task 9: Alerts

**Files:**
- Modify: `backend/app/services/alerts.py`
- Test: extend `backend/tests/test_alerts.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_card_payment_due_alert_within_lead_days(client, auth, card_with_cycle_due_in_3_days):
    # GET /api/alerts/generate (or the read endpoint that triggers it)
    # -> one alert kind "card_payment_due", payload account_id, message has amount
    # second generate call -> 0 created (idempotent)

def test_card_payment_due_not_before_lead(client, auth, card_due_in_4_days):
    # -> no card_payment_due alert

def test_instalment_due_alert_within_lead_days(client, auth, plan_due_in_2_days):
    # -> one "instalment_due" alert, payload plan_id; idempotent
    # paused plan -> no alert
```

Helper: to control "due in N days" without time travel, pick `statement_day`/`payment_due_days` (and `first_due_date`) arithmetically against `date.today()`.

- [ ] **Step 2: Run to verify failure** → Expected: FAIL (kinds missing)

- [ ] **Step 3: Implement in `generate_alerts`**

After the overdue-rules block:

```python
    CARD_DUE_LEAD_DAYS = 3
    for account in db.scalars(select(Account).where(
        Account.household_id == household_id, Account.kind == "credit",
        Account.statement_day.is_not(None), Account.payment_due_days.is_not(None),
        Account.owner_id.is_(None),
    )):
        due = payment_due_date(next_statement_date(account.statement_day, today), account.payment_due_days)
        if not (0 <= (due - today).days <= CARD_DUE_LEAD_DAYS):
            continue
        sums = db.execute(
            select(func.coalesce(Transaction.transfer_direction, Transaction.type), func.sum(Transaction.amount))
            .join(... ) # reuse balance_sums for this account instead:
        )
        # simpler: card_balance via balance_sums(db, household_id, Account.id == account.id)
        outstanding = max(0.0, -card_balance)
        if _create_once(
            db, household_id=household_id, user_id=None, kind="card_payment_due",
            message=f"El pago de la tarjeta \"{account.name}\" vence el {due.isoformat()} (≈ {outstanding:,.2f}).",
            payload={"account_id": account.id, "due_date": due.isoformat(), "estimated_amount": round(outstanding, 2)},
            dedupe_key=f"card_due:{account.id}:{due.isoformat()}",
        ):
            created += 1

    for plan in db.scalars(select(InstalmentPlan).where(
        InstalmentPlan.household_id == household_id, InstalmentPlan.status == "active",
    )):
        nxt = next_unpaid_due(plan)
        if not nxt or not (0 <= (nxt[0] - today).days <= INSTALMENT_DUE_LEAD_DAYS):
            continue
        if _create_once(
            db, household_id=household_id, user_id=None, kind="instalment_due",
            message=f"Vence el instalado {plan.paid_count + 1}/{plan.months} ({nxt[1]:,.2f}) el {nxt[0].isoformat()}.",
            payload={"plan_id": plan.id, "source_transaction_id": plan.source_transaction_id, "due_date": nxt[0].isoformat()},
            dedupe_key=f"instalment_due:{plan.id}:{nxt[0].isoformat()}",
        ):
            created += 1
```

(Use the existing `balance_sums` helper for the card balance — do not hand-roll the SQL.)

- [ ] **Step 4: Run tests** → Expected: PASS; full suite green.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/alerts.py backend/tests/test_alerts.py
git commit -m "Add card payment due and instalment due alerts"
```

---

## Chunk 5: Frontend

### Task 10: Types and queries

**Files:**
- Modify: `frontend/src/lib/types.ts`
- Modify: `frontend/src/lib/queries.ts`

- [ ] **Step 1: Types**

`Account`: add `statementDay?: number | null`, `paymentDueDays?: number | null`, `nextStatementDate?: string | null`, `lastStatementDate?: string | null`, `nextPaymentDueDate?: string | null`.

`ForecastUpcoming.source`: `"transaction" | "recurring" | "card_due" | "instalment_due"`.

`AlertKind` (existing union): add `"card_payment_due" | "instalment_due"`.

New:

```ts
export interface InstalmentScheduleItem {
  date: string
  amount: number
  paid: boolean
}

export interface InstalmentPlan {
  id: string
  householdId: string
  accountId: string
  accountName: string
  sourceTransactionId: string
  months: number
  totalAmount: number
  monthlyAmount: number
  firstDueDate: string
  paidCount: number
  status: "active" | "paused" | "completed" | "cancelled"
  nextDueDate?: string | null
  nextDueAmount?: number | null
  schedule: InstalmentScheduleItem[]
  createdAt: string
}
```

- [ ] **Step 2: Queries (follow the existing hook patterns in `queries.ts`)**

```ts
export function useInstalmentPlans() {
  return useQuery({ queryKey: ["instalment-plans"], queryFn: () => apiFetch<InstalmentPlan[]>("/instalment-plans") })
}
export function useInstalmentPlan(id: string | undefined) {
  return useQuery({ queryKey: ["instalment-plans", id], enabled: !!id, queryFn: () => apiFetch<InstalmentPlan>(`/instalment-plans/${id}`) })
}
```

Mutations: `useCreateInstalmentPlan`, `usePayInstalmentPlan`, `usePauseInstalmentPlan`, `useResumeInstalmentPlan`, `useCancelInstalmentPlan`. Each invalidates: `instalment-plans`, `accounts`, `transactions`, `forecast`, `alerts` (the pay-with-transfer mutation also `summary`).

- [ ] **Step 3: Verify**

Run: `cd frontend && npx tsc -b` → Expected: no errors

- [ ] **Step 4: Commit**

```bash
git add frontend/src/lib/types.ts frontend/src/lib/queries.ts
git commit -m "Add frontend types and queries for card cycle and instalment plans"
```

### Task 11: Account form and list

**Files:**
- Modify: `frontend/src/components/AccountFormSheet.tsx`
- Modify: `frontend/src/pages/AccountsPage.tsx` (and the account card widget if it renders meta)

- [ ] **Step 1: AccountFormSheet**

- State: `statementDay: string`, `paymentDueDays: string` (empty = null).
- When `kind === "credit"`: show a "Ciclo de la tarjeta" section with two number inputs — "Día de corte (1–28)" and "Días hasta el pago (default 20, 1–60)".
- On submit: include `statementDay: number | null` and `paymentDueDays: number | null` (null when empty or kind != credit; when kind switches away from credit, send null to clear — the backend requires it).
- On edit of an existing account: prefill from the account.

- [ ] **Step 2: AccountsPage / card widget**

For credit accounts with a cycle: render a chip `Corte {statementDay} · Pago {nextPaymentDueDate formatted}` (e.g. "Corte 15 · Pago 4 sep") using `nextPaymentDueDate`. Under each credit account, list its active/paused plans (from `useInstalmentPlans()` filtered by `accountId`) as compact rows: `MSI $850 × 6 · 3/6 · próx. 31 ago` → tap opens the plan sheet (Task 12). Paused plans show "pausado".

- [ ] **Step 3: Verify**

Run: `cd frontend && npm run lint && npx tsc -b` → Expected: pass

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/AccountFormSheet.tsx frontend/src/pages/AccountsPage.tsx
git commit -m "Add card cycle to the account form and list"
```

### Task 12: Instalment plan sheets and transaction badge

**Files:**
- Create: `frontend/src/components/InstalmentPlanSheets.tsx`
- Modify: `frontend/src/components/TransactionDetailSheet.tsx`

- [ ] **Step 1: `InstalmentPlanSheets.tsx`** (model on `SavingsGoalSheets.tsx`)

- `InstalmentPlanCreateSheet({ open, onOpenChange, transaction, account })`:
  - Inputs: months (number 2–48), firstDueDate (date input; default `account.nextPaymentDueDate ?? transaction.date + 1 month`).
  - Live preview: monthly amount + "la última cuota ajusta el redondeo" note.
  - Create via `useCreateInstalmentPlan`; close on success.
- `InstalmentPlanSheet({ open, onOpenChange, planId })`:
  - Header: plan summary (`$X × N · tarjeta`), status chip.
  - Progress bar `paidCount/months`.
  - Schedule list: each row date + signed amount + paid check; next unpaid highlighted.
  - Actions (active only): "Registrar pago ahora" (pick source from shared cash/debit/savings accounts, defaults to first cash account → `pay` with `sourceAccountId` + today), "Marcar pagado" (no transfer), "Pausar"/"Reanudar", "Cancelar plan" (two-step confirm, like the existing delete pattern).
  - All amounts respect the balance-concealment toggle where the sheet renders inside a concealing context (follow the pattern in `SavingsGoalSheets.tsx`).

- [ ] **Step 2: `TransactionDetailSheet.tsx`**

When the transaction is an expense on a credit account:
- If a plan exists for `transaction.id` (from `useInstalmentPlans()`): show a badge row `MSI · $850 × 6 · 3 pagados · próx. 31 ago` → tap opens `InstalmentPlanSheet`.
- Else (and only when the account is `kind === "credit"` and shared): a "Crear plan MSI" button → `InstalmentPlanCreateSheet`.

- [ ] **Step 3: Verify**

Run: `cd frontend && npm run lint && npx tsc -b` → Expected: pass

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/InstalmentPlanSheets.tsx frontend/src/components/TransactionDetailSheet.tsx
git commit -m "Add instalment plan sheets and transaction badge"
```

### Task 13: Alerts rendering (forecast needs no change)

**Files:**
- Modify: `frontend/src/components/AlertsSheet.tsx`

- [ ] **Step 1: Extend `alertVisual` and `destination`**

```ts
card_payment_due: { icon: CreditCard, tone: "bg-primary/12 text-primary" },
instalment_due: { icon: CalendarClock, tone: "bg-primary/12 text-primary" },
// destination(): both -> "/app/cuentas"
```

Import `CreditCard` from `lucide-react`. (The dashboard `ForecastCard` already renders any upcoming event with label + signed amount; the new `source` values flow through — verify in the build, no code change expected.)

- [ ] **Step 2: Verify**

Run: `cd frontend && npm run lint && npm run build` → Expected: pass

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/AlertsSheet.tsx
git commit -m "Render card and instalment alert kinds"
```

---

## Chunk 6: Verification and docs

### Task 14: Full verification + roadmap update

**Files:**
- Modify: `docs/roadmap/README.md`, `docs/roadmap/23-tarjetas-mx-e-instalados.md`, `docs/plan.md`

- [ ] **Step 1: Backend**

Run: `cd backend && uv run pytest -q` → Expected: all pass (210+ new).
Run (if Postgres available locally, otherwise rely on CI): `docker run --rm -d --name pg-migtest -p 55432:5432 -e POSTGRES_USER=budget -e POSTGRES_PASSWORD=budget -e POSTGRES_DB=budget postgres:17-alpine` then `MIGRATIONS_TEST_DATABASE_URL=postgresql+psycopg://budget:budget@localhost:55432/postgres uv run pytest tests/test_migrations.py -q` → Expected: pass (schema == models, reversible, data survives).

- [ ] **Step 2: Frontend**

Run: `cd frontend && npm run lint && npm run build` → Expected: pass (pre-existing chunk-size warning acceptable).

- [ ] **Step 3: Manual browser pass** (stack up via `docker compose up -d --build`)

Check: create credit account with cycle → chip + derived dates; create purchase → plan sheet → schedule; record payment (transfer) → balances move, expense totals unchanged; forecast shows the two new events; bell shows the due alerts; pause/cancel flows; two-step delete of a planned purchase is blocked with 409 copy.

- [ ] **Step 4: Docs**

- `docs/roadmap/23-tarjetas-mx-e-instalados.md`: header `**Status:** ✅ 2026-08-16`.
- `docs/roadmap/README.md`: row 23 → `✅ 2026-08-16`; progress line → `23 of 24 done ... 24 proposed`; append a dated log entry summarizing the implementation (mirror the style of the 2026-08-15 entry).
- `docs/plan.md`: move the 23 line from Proposed to the next-cycle Progress list as ✅.

- [ ] **Step 5: Commit**

```bash
git add docs/
git commit -m "Mark roadmap 23 (Mexican cards and instalments) done"
```

- [ ] **Step 6: Push + PR**

```bash
git push -u origin feat/mexican-cards-instalments
gh pr create  # Summary / Changes / Test plan per repo convention
```
