"""Balance formula derived from the ledger.

`list_accounts`, the cash-flow forecast, and any other consumer compute
from here so the formula cannot drift:
`opening_balance + income + inflow − expense − outflow`, with
`deleted_at IS NULL`.
"""

from sqlalchemy import func, select

from app.models import Account, Transaction


def balance_sums(db, household_id: str, visibility) -> dict[str, dict[str, float]]:
    """Sum of amounts per account and cash type (income, expense, inflow, outflow).

    `visibility` is a predicate over `Account` (`visible_accounts`,
    `shared_accounts`, or any equivalent filter).
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
    sums: dict[str, dict[str, float]] = {}
    for account_id, tx_type, total in totals:
        sums.setdefault(account_id, {})[tx_type] = float(total or 0)
    return sums


def account_balance(opening_balance: float | str, sums: dict[str, float]) -> float:
    """Account balance from its per-type sums.

    Accepts `opening_balance` as `Numeric`/`Decimal` straight from the model.
    """
    return (
        float(opening_balance)
        + sums.get("income", 0.0)
        + sums.get("inflow", 0.0)
        - sums.get("expense", 0.0)
        - sums.get("outflow", 0.0)
    )
