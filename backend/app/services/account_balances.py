"""Fórmula de saldo derivada del libro mayor.

`list_accounts`, la proyección de flujo de efectivo y cualquier otro
consumidor calculan desde aquí para que la fórmula no se desincronice:
`opening_balance + income + inflow − expense − outflow`, con
`deleted_at IS NULL`.
"""

from sqlalchemy import func, select

from app.models import Account, Transaction


def balance_sums(db, household_id: str, visibility) -> dict[str, dict[str, float]]:
    """Suma de montos por cuenta y tipo efectivo (income, expense, inflow, outflow).

    `visibility` es un predicado sobre `Account` (`visible_accounts`,
    `shared_accounts` o cualquier filtro equivalente).
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
    """Saldo de una cuenta a partir de sus sumas por tipo.

    Acepta `opening_balance` como `Numeric`/`Decimal` directo del modelo.
    """
    return (
        float(opening_balance)
        + sums.get("income", 0.0)
        + sums.get("inflow", 0.0)
        - sums.get("expense", 0.0)
        - sums.get("outflow", 0.0)
    )
