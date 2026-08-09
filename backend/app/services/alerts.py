"""Lazy, idempotent financial alert generation for self-hosted deployments."""

from datetime import date

from sqlalchemy import case, extract, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Account, Alert, Budget, RecurringRule, SavingsGoal, Transaction, TransactionSplit

OVERDUE_RULE_DAYS = 3


def _create_once(
    db: Session, *, household_id: str, user_id: str | None, kind: str,
    message: str, payload: dict, dedupe_key: str,
) -> bool:
    """The unique constraint, rather than a prior read, closes concurrent races."""
    try:
        with db.begin_nested():
            db.add(Alert(
                household_id=household_id, user_id=user_id, kind=kind,
                message=message, payload=payload, dedupe_key=dedupe_key,
            ))
            db.flush()
        return True
    except IntegrityError:
        return False


def _effective_budgets(budgets: list[Budget], month: date) -> dict[str, Budget]:
    result = {budget.category_id: budget for budget in budgets if budget.month is None}
    result.update({budget.category_id: budget for budget in budgets if budget.month == month})
    return result


def _budget_spend(db: Session, household_id: str, category_ids: list[str], today: date) -> dict[str, float]:
    if not category_ids:
        return {}
    filters = (
        Transaction.household_id == household_id,
        Transaction.deleted_at.is_(None),
        Account.owner_id.is_(None),
        Transaction.type == "expense",
        extract("year", Transaction.date) == today.year,
        extract("month", Transaction.date) == today.month,
    )
    simple = db.execute(
        select(Transaction.category_id, func.sum(Transaction.amount))
        .join(Account)
        .where(*filters, Transaction.is_split.is_(False), Transaction.category_id.in_(category_ids))
        .group_by(Transaction.category_id)
    ).all()
    split = db.execute(
        select(TransactionSplit.category_id, func.sum(TransactionSplit.amount))
        .join(Transaction, Transaction.id == TransactionSplit.transaction_id)
        .join(Account, Account.id == Transaction.account_id)
        .where(*filters, Transaction.is_split.is_(True), TransactionSplit.category_id.in_(category_ids))
        .group_by(TransactionSplit.category_id)
    ).all()
    amounts: dict[str, float] = {}
    for category_id, amount in [*simple, *split]:
        amounts[category_id] = amounts.get(category_id, 0) + float(amount)
    return amounts


def generate_alerts(db: Session, household_id: str, today: date | None = None) -> int:
    """Persist newly applicable alerts and return how many were created."""
    today = today or date.today()
    created = 0
    month = today.replace(day=1)

    budgets = db.scalars(select(Budget).where(Budget.household_id == household_id)).all()
    effective = _effective_budgets(budgets, month)
    spent = _budget_spend(db, household_id, list(effective), today)
    for category_id, budget in effective.items():
        amount = float(budget.amount)
        if amount <= 0:
            continue
        percentage = spent.get(category_id, 0) / amount * 100
        period = month.isoformat()
        if percentage >= 100 and _create_once(
            db, household_id=household_id, user_id=None, kind="budget_exceeded",
            message=f"El presupuesto de esta categoría superó su límite ({percentage:.0f}%).",
            payload={"category_id": category_id, "month": period},
            dedupe_key=f"budget_exceeded:{category_id}:{period}",
        ):
            created += 1
        if percentage >= 75 and _create_once(
            db, household_id=household_id, user_id=None, kind="budget_warning",
            message=f"El presupuesto de esta categoría ya alcanzó {percentage:.0f}%.",
            payload={"category_id": category_id, "month": period},
            dedupe_key=f"budget_warning:{category_id}:{period}",
        ):
            created += 1

    overdue_before = today.fromordinal(today.toordinal() - OVERDUE_RULE_DAYS)
    rules = db.execute(
        select(RecurringRule, Account.owner_id)
        .join(Account, Account.id == RecurringRule.account_id)
        .where(RecurringRule.household_id == household_id, RecurringRule.active.is_(True), RecurringRule.next_run_date <= overdue_before)
    ).all()
    for rule, owner_id in rules:
        if _create_once(
            db, household_id=household_id, user_id=owner_id, kind="recurring_overdue",
            message=f"Una regla recurrente está vencida desde el {rule.next_run_date.isoformat()}.",
            payload={"recurring_rule_id": rule.id}, dedupe_key=f"recurring_overdue:{rule.id}:{rule.next_run_date.isoformat()}",
        ):
            created += 1

    goals = db.scalars(select(SavingsGoal).where(
        SavingsGoal.household_id == household_id, SavingsGoal.archived.is_(False),
        SavingsGoal.current_amount >= SavingsGoal.target_amount,
    )).all()
    for goal in goals:
        if _create_once(
            db, household_id=household_id, user_id=None, kind="goal_reached",
            message=f"La meta \"{goal.name}\" ya fue alcanzada.", payload={"goal_id": goal.id},
            dedupe_key=f"goal_reached:{goal.id}",
        ):
            created += 1

    balance = func.coalesce(func.sum(case(
        (Transaction.type == "income", Transaction.amount),
        (Transaction.type == "expense", -Transaction.amount),
        (Transaction.transfer_direction == "inflow", Transaction.amount),
        else_=-Transaction.amount,
    )), 0)
    accounts = db.execute(
        select(Account, balance.label("balance"))
        .outerjoin(Transaction, (Transaction.account_id == Account.id) & Transaction.deleted_at.is_(None))
        .where(Account.household_id == household_id)
        .group_by(Account.id)
        .having(Account.opening_balance + balance < 0)
    ).all()
    for account, current_balance in accounts:
        if _create_once(
            db, household_id=household_id, user_id=account.owner_id, kind="negative_balance",
            message=f"La cuenta \"{account.name}\" tiene saldo negativo.",
            payload={"account_id": account.id, "balance": float(current_balance) + float(account.opening_balance)},
            dedupe_key=f"negative_balance:{account.id}",
        ):
            created += 1

    if created:
        db.commit()
    return created
