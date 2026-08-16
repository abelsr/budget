"""Proyección diaria del flujo de efectivo del hogar.

Lectura puramente derivada: no inserta transacciones ni avanza
`next_run_date` (el estado vive ahí). El endpoint llama antes a
`materialize_due` —convención de todos los endpoints de lectura—, que es
idempotente y garantiza que no falte ninguna ocurrencia vencida en el
opening balance.

Entrada de la proyección, en orden:
1. Saldo actual del hogar (solo cuentas compartidas, misma fórmula que
   `GET /accounts` vía `account_balances`). Esa fórmula **no filtra por
   fecha**: un movimiento registrado con fecha futura ya está incluido aquí,
   así que volver a aplicarlo como delta diario lo contaría dos veces. Por
   eso el walk solo suma ocurrencias **aún no materializadas** (recurrentes).
2. Ocurrencias futuras de reglas recurrentes activas en cuentas
   compartidas, proyectadas con `advance()` sin materializar.
Los movimientos registrados con fecha futura (incluido transfer, excluidos
los soft-deleted) no entran al walk: solo aparecen en la lista `upcoming`.
"""

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Account, Category, RecurringRule, Transaction
from app.services.account_access import shared_accounts
from app.services.account_balances import account_balance, balance_sums
from app.services.recurring import advance

#: Ventana fija de la lista de próximos movimientos, en días.
UPCOMING_WINDOW_DAYS = 30
#: Tope de eventos en la lista de próximos movimientos.
UPCOMING_LIMIT = 20


@dataclass(frozen=True)
class ForecastPoint:
    date: date
    income: float
    expense: float
    delta: float
    balance: float


@dataclass(frozen=True)
class UpcomingEvent:
    date: date
    #: Efecto sobre la caja compartida: "income" entra, "expense" sale. Un
    #: transfer a futuro se reporta por ese efecto (vía compartida → "expense",
    #: hacia compartida → "income"); un transfer entre dos cuentas
    #: compartidas no aparece porque no mueve la caja del hogar.
    type: str
    amount: float
    label: str
    source: str


@dataclass(frozen=True)
class ForecastResult:
    as_of: date
    days: int
    opening_balance: float
    points: tuple[ForecastPoint, ...]
    upcoming: tuple[UpcomingEvent, ...]


def _project_rule(
    rule: RecurringRule,
    as_of: date,
    horizon: date,
    window_end: date,
    category_names: dict[str, str],
    income_by_date: dict,
    expense_by_date: dict,
    delta_by_date: dict,
    events: list[UpcomingEvent],
) -> None:
    """Encadena `advance()` desde `next_run_date` hasta pasar el horizonte.

    El clamp mensual de `anchor_day` (ene 31 → feb 28 → mar 31) lo define
    `advance()`; aquí solo se recorre, sin reimplementar calendario.
    """
    amount = float(rule.amount)
    current = rule.next_run_date
    while current <= horizon:
        if current > as_of:
            if rule.type == "income":
                income_by_date[current] += amount
                delta_by_date[current] += amount
            else:
                expense_by_date[current] += amount
                delta_by_date[current] -= amount
            if current <= window_end:
                events.append(
                    UpcomingEvent(
                        date=current,
                        type=rule.type,
                        amount=amount,
                        label=rule.note or category_names.get(rule.category_id) or "Recurrente",
                        source="recurring",
                    )
                )
        current = advance(current, rule.frequency, rule.anchor_day)


def build_forecast(db: Session, household_id: str, as_of: date, days: int) -> ForecastResult:
    """Serie de `days + 1` filas desde `as_of` (la primera con delta 0).

    Invariante: el balance final coincide con el opening balance más la suma
    de los deltas, todo redondeado a 2 decimales por fila.
    """
    horizon = as_of + timedelta(days=days)
    window_end = as_of + timedelta(days=UPCOMING_WINDOW_DAYS)

    # Saldo inicial: misma fórmula que GET /accounts, solo cuentas compartidas.
    shared = {
        account.id: account
        for account in db.scalars(select(Account).where(Account.household_id == household_id, shared_accounts()))
    }
    account_sums = balance_sums(db, household_id, shared_accounts())
    opening = round(
        sum(account_balance(account.opening_balance, account_sums.get(account.id, {})) for account in shared.values()),
        2,
    )

    category_names = dict(
        db.execute(select(Category.id, Category.name).where(Category.household_id == household_id)).all()
    )

    income_by_date: dict[date, float] = defaultdict(float)
    expense_by_date: dict[date, float] = defaultdict(float)
    delta_by_date: dict[date, float] = defaultdict(float)
    events: list[UpcomingEvent] = []
    upcoming_transfers: dict[str, list[Transaction]] = defaultdict(list)

    # Solo para `upcoming`: los movimientos registrados (pasados o futuros)
    # ya figuran en el opening balance (la fórmula no filtra por fecha), por
    # lo que no deben repetirse como delta en la serie.
    for tx in db.scalars(
        select(Transaction)
        .join(Account, Account.id == Transaction.account_id)
        .where(
            Transaction.household_id == household_id,
            Transaction.deleted_at.is_(None),
            shared_accounts(),
            Transaction.date > as_of,
            Transaction.date <= window_end,
        )
        .order_by(Transaction.date)
    ).all():
        amount = float(tx.amount)
        if tx.type == "transfer":
            upcoming_transfers[tx.transfer_group_id or tx.id].append(tx)
            continue
        events.append(
            UpcomingEvent(
                date=tx.date,
                type=tx.type,
                amount=amount,
                label=tx.note or category_names.get(tx.category_id or "") or "Movimiento",
                source="transaction",
            )
        )

    # Un grupo con dos filas aquí ⇒ ambas cuentas compartidas: la caja del
    # hogar no cambia, no se lista. Una sola fila ⇒ el otro extremo es
    # personal y el efecto sobre la caja compartida sí se lista.
    for rows in upcoming_transfers.values():
        if len(rows) != 1:
            continue
        tx = rows[0]
        events.append(
            UpcomingEvent(
                date=tx.date,
                type="income" if tx.transfer_direction == "inflow" else "expense",
                amount=float(tx.amount),
                label=tx.note or "Transferencia",
                source="transaction",
            )
        )

    for rule in db.scalars(
        select(RecurringRule).where(
            RecurringRule.household_id == household_id,
            RecurringRule.active.is_(True),
        )
    ):
        if rule.account_id not in shared:
            continue
        _project_rule(
            rule, as_of, horizon, window_end, category_names,
            income_by_date, expense_by_date, delta_by_date, events,
        )

    events.sort(key=lambda event: (event.date, event.source, event.type, event.label))
    events = events[:UPCOMING_LIMIT]

    points: list[ForecastPoint] = []
    running = opening
    for offset in range(days + 1):
        day = as_of + timedelta(days=offset)
        delta = round(delta_by_date.get(day, 0.0), 2)
        running = round(running + delta, 2)
        points.append(
            ForecastPoint(
                date=day,
                income=round(income_by_date.get(day, 0.0), 2),
                expense=round(expense_by_date.get(day, 0.0), 2),
                delta=delta,
                balance=running,
            )
        )

    return ForecastResult(
        as_of=as_of,
        days=days,
        opening_balance=opening,
        points=tuple(points),
        upcoming=tuple(events),
    )
