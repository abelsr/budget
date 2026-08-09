from datetime import date, datetime, timezone
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import extract, func, select

from app.api.deps import CurrentUserDep, DbDep
from app.models import Account, Budget, Category, Transaction, TransactionSplit, User
from app.schemas.budgets import BudgetCreate, BudgetOut, BudgetStatus, BudgetUpdate
from app.services.recurring import materialize_due
from app.services.account_access import shared_accounts

router = APIRouter(prefix="/budgets", tags=["budgets"])

_MONTH_PATTERN = r"^\d{4}-\d{2}$"


def _household_id(user: User) -> str:
    if user.household_id is None:
        raise HTTPException(status_code=400, detail="El usuario no pertenece a un hogar")
    return user.household_id


def _get_budget(db, household_id: str, budget_id: str) -> Budget:
    budget = db.get(Budget, budget_id)
    if budget is None or budget.household_id != household_id:
        raise HTTPException(status_code=404, detail="Presupuesto no encontrado")
    return budget


def _get_expense_category(db, household_id: str, category_id: str) -> Category:
    category = db.get(Category, category_id)
    if category is None or category.household_id != household_id or category.deleted:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    if category.type != "expense":
        raise HTTPException(
            status_code=422, detail="Solo se pueden presupuestar categorías de gasto"
        )
    return category


def _budget_out(budget: Budget) -> BudgetOut:
    return BudgetOut(
        id=budget.id,
        household_id=budget.household_id,
        category_id=budget.category_id,
        amount=float(budget.amount),
        month=budget.month,
        rollover=budget.rollover,
    )


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _spent_by_category(
    db, household_id: str, category_ids: list[str], year: int, month_num: int
) -> dict[str, object]:
    if not category_ids:
        return {}

    base_filter = [
        Transaction.household_id == household_id,
        Transaction.deleted_at.is_(None),
        shared_accounts(),
        extract("year", Transaction.date) == year,
        extract("month", Transaction.date) == month_num,
        Transaction.type == "expense",
    ]
    split_stmt = (
        select(TransactionSplit.category_id, func.sum(TransactionSplit.amount))
        .join(Transaction, Transaction.id == TransactionSplit.transaction_id)
        .join(Account, Account.id == Transaction.account_id)
        .where(*base_filter, Transaction.is_split.is_(True))
        .where(TransactionSplit.category_id.in_(category_ids))
        .group_by(TransactionSplit.category_id)
    )
    simple_stmt = (
        select(Transaction.category_id, func.sum(Transaction.amount))
        .join(Account)
        .where(*base_filter, Transaction.is_split.is_(False))
        .where(Transaction.category_id.in_(category_ids))
        .group_by(Transaction.category_id)
    )
    spent: dict[str, object] = {}
    for category_id, amount in [*db.execute(split_stmt).all(), *db.execute(simple_stmt).all()]:
        spent[category_id] = spent.get(category_id, 0) + amount
    return spent


def _effective_budgets(budgets: list[Budget], month: date) -> dict[str, Budget]:
    effective = {budget.category_id: budget for budget in budgets if budget.month is None}
    effective.update(
        {budget.category_id: budget for budget in budgets if budget.month == month}
    )
    return effective


def _available_amount(
    budget: Budget, previous: Budget | None, previous_spent: object
) -> float:
    if previous is None or not previous.rollover:
        return float(budget.amount)
    return float(budget.amount) + max(0, float(previous.amount) - float(previous_spent))


@router.get("")
def list_budgets(db: DbDep, user: CurrentUserDep) -> list[BudgetOut]:
    household_id = _household_id(user)
    budgets = db.scalars(
        select(Budget)
        .where(Budget.household_id == household_id)
        .order_by(Budget.category_id, Budget.month)
    ).all()
    return [_budget_out(b) for b in budgets]


@router.get("/status")
def get_budgets_status(
    db: DbDep,
    user: CurrentUserDep,
    month: Annotated[str | None, Query(pattern=_MONTH_PATTERN)] = None,
) -> list[BudgetStatus]:
    household_id = _household_id(user)
    materialize_due(db, household_id, user.id)

    budgets = db.scalars(
        select(Budget).where(Budget.household_id == household_id)
    ).all()
    if not budgets:
        return []

    if month is None:
        now = _now()
        year, month_num = now.year, now.month
    else:
        year, month_num = int(month[:4]), int(month[5:7])
        if not 1 <= month_num <= 12:
            raise HTTPException(status_code=422, detail="Mes inválido")

    current_month = date(year, month_num, 1)
    previous_month = date(year - 1, 12, 1) if month_num == 1 else date(year, month_num - 1, 1)
    effective = _effective_budgets(budgets, current_month)
    previous = _effective_budgets(budgets, previous_month)
    category_ids = list(effective)
    spent_by_category = _spent_by_category(db, household_id, category_ids, year, month_num)
    rollover_ids = [
        category_id
        for category_id in category_ids
        if (previous_budget := previous.get(category_id)) is not None and previous_budget.rollover
    ]
    previous_spent = _spent_by_category(
        db, household_id, rollover_ids, previous_month.year, previous_month.month
    )

    return [
        BudgetStatus(
            category_id=category_id,
            budget=float(budget.amount),
            available=round(
                _available_amount(
                    budget, previous.get(category_id), previous_spent.get(category_id, 0)
                ),
                2,
            ),
            spent=round(float(spent_by_category.get(category_id, 0)), 2),
            percentage=round(
                float(spent_by_category.get(category_id, 0))
                / _available_amount(
                    budget, previous.get(category_id), previous_spent.get(category_id, 0)
                )
                * 100,
                1,
            ),
        )
        for category_id, budget in effective.items()
    ]


@router.post("", status_code=201)
def create_budget(
    payload: BudgetCreate, db: DbDep, user: CurrentUserDep
) -> BudgetOut:
    household_id = _household_id(user)
    _get_expense_category(db, household_id, payload.category_id)
    scope = Budget.month.is_(None) if payload.month is None else Budget.month == payload.month
    existing = db.scalar(
        select(Budget).where(
            Budget.household_id == household_id,
            Budget.category_id == payload.category_id,
            scope,
        )
    )
    if existing is not None:
        raise HTTPException(
            status_code=409, detail="Ya existe un presupuesto para esta categoría y mes"
        )
    budget = Budget(
        household_id=household_id,
        category_id=payload.category_id,
        amount=payload.amount,
        month=payload.month,
        rollover=payload.rollover,
    )
    db.add(budget)
    db.commit()
    db.refresh(budget)
    return _budget_out(budget)


@router.patch("/{budget_id}")
def update_budget(
    budget_id: str, payload: BudgetUpdate, db: DbDep, user: CurrentUserDep
) -> BudgetOut:
    household_id = _household_id(user)
    budget = _get_budget(db, household_id, budget_id)
    budget.amount = payload.amount
    if payload.rollover is not None:
        budget.rollover = payload.rollover
    db.commit()
    db.refresh(budget)
    return _budget_out(budget)


@router.delete("/{budget_id}", status_code=204)
def delete_budget(budget_id: str, db: DbDep, user: CurrentUserDep) -> None:
    household_id = _household_id(user)
    budget = _get_budget(db, household_id, budget_id)
    db.delete(budget)
    db.commit()
