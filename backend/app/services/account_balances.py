"""Balance formula derived from the ledger.

`list_accounts`, the cash-flow forecast, and any other consumer compute
from here so the formula cannot drift:
`opening_balance + income + inflow − expense − outflow`, with
`deleted_at IS NULL`.

Money stays `Decimal` all the way through the accumulation: the columns are
`Numeric(19, 4)`, so SQLAlchemy (and `func.sum`) already yield exact
`Decimal`. Summing those in `Decimal` avoids the `0.1 + 0.2`-style binary
artifacts a float accumulation would introduce; the single `float` cast at
the end keeps the long-standing `float` contract of every consumer without
rounding at each intermediate step.
"""

from decimal import Decimal

from sqlalchemy import func, select

from app.models import Account, Transaction


def balance_sums(db, household_id: str, visibility) -> dict[str, dict[str, Decimal]]:
    """Sum of amounts per account and cash type (income, expense, inflow, outflow).

    `visibility` is a predicate over `Account` (`visible_accounts`,
    `shared_accounts`, or any equivalent filter).

    Returns exact `Decimal` sums per account and cash type — do not convert to
    `float` here, or the precision benefit is lost before `account_balance`.
    """
    totals = db.execute(
        select(
            Account.id,
            func.coalesce(Transaction.transfer_direction, Transaction.type),
            func.sum(Transaction.amount),
        )
        .join(Transaction, Transaction.account_id == Account.id)
        .where(
            Account.household_id == household_id,
            Transaction.deleted_at.is_(None),
            visibility,
        )
        .group_by(Account.id, func.coalesce(Transaction.transfer_direction, Transaction.type))
    ).all()
    sums: dict[str, dict[str, Decimal]] = {}
    for account_id, tx_type, total in totals:
        sums.setdefault(account_id, {})[tx_type] = Decimal(total) if total is not None else Decimal(0)
    return sums


def account_balance(opening_balance: Decimal | float, sums: dict[str, Decimal]) -> float:
    """Account balance from its per-type sums.

    `opening_balance` and every sum are accumulated in exact `Decimal`
    (`Numeric` columns yield `Decimal`), then cast to `float` once so the
    return type stays the `float` contract every consumer relies on.
    """
    ob = opening_balance if isinstance(opening_balance, Decimal) else Decimal(str(opening_balance))
    balance = (
        ob
        + sums.get("income", Decimal(0))
        + sums.get("inflow", Decimal(0))
        - sums.get("expense", Decimal(0))
        - sums.get("outflow", Decimal(0))
    )
    return float(balance)
