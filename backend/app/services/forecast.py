"""Day-by-day cash-flow forecast of the household balance.

Purely derived read: it inserts no transactions and does not advance
`next_run_date` (the state lives there). The endpoint calls
`materialize_due` first, per the convention of every read endpoint, which
is idempotent and guarantees no overdue occurrence is missing from the
opening balance.

Projection inputs, in order:
1. Current household balance (shared accounts only, same formula as
   `GET /accounts` via `account_balances`). That formula is **not filtered
   by date**: a movement recorded with a future date is already included
   here, so applying it again as a daily delta would count it twice. The
   walk therefore only adds occurrences **not yet materialized** (recurring
   rules).
2. Future occurrences of active recurring rules on shared accounts,
   projected with `advance()` without materializing them.
Recorded movements with a future date (transfers included, soft-deleted
excluded) do not enter the walk: they only appear in the `upcoming` list.
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

#: Fixed window of the upcoming-movements list, in days.
UPCOMING_WINDOW_DAYS = 30
#: Cap on events in the upcoming-movements list.
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
    #: Effect on the shared household cash: "income" comes in, "expense"
    #: goes out. A future transfer is reported by that effect (from a shared
    #: account -> "expense", into a shared account -> "income"); a transfer
    #: between two shared accounts does not appear because it does not move
    #: household cash.
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
    """Chain `advance()` from `next_run_date` until past the horizon.

    The monthly `anchor_day` clamp (Jan 31 -> Feb 28 -> Mar 31) is defined
    by `advance()`; this only walks it, without reimplementing the calendar.
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
    """Series of `days + 1` rows from `as_of` (the first with delta 0).

    Invariant: the final balance equals the opening balance plus the sum of
    the deltas, rounded to 2 decimals per row.
    """
    horizon = as_of + timedelta(days=days)
    window_end = as_of + timedelta(days=UPCOMING_WINDOW_DAYS)

    # Opening balance: same formula as GET /accounts, shared accounts only.
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

    # Only for `upcoming`: recorded movements (past or future) are already
    # in the opening balance (the formula is not filtered by date), so they
    # must not be repeated as a delta in the series.
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

    # A group with two rows here means both accounts are shared: household
    # cash does not change, so it is not listed. One row means the other end
    # is personal and the effect on shared cash is listed.
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
