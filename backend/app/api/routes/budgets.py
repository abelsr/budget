from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import extract, func, select

from app.api.deps import CurrentUserDep, DbDep
from app.models import Account, Budget, Category, Transaction, User
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
    )


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


@router.get("")
def list_budgets(db: DbDep, user: CurrentUserDep) -> list[BudgetOut]:
    household_id = _household_id(user)
    budgets = db.scalars(
        select(Budget).where(Budget.household_id == household_id)
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

    category_ids = [b.category_id for b in budgets]
    base_filter = [
        Transaction.household_id == household_id,
        shared_accounts(),
        extract("year", Transaction.date) == year,
        extract("month", Transaction.date) == month_num,
        Transaction.type == "expense",
        Transaction.category_id.in_(category_ids),
    ]
    spent_stmt = (
        select(Transaction.category_id, func.sum(Transaction.amount)).join(Account)
        .where(*base_filter)
        .group_by(Transaction.category_id)
    )
    spent_by_category = dict(db.execute(spent_stmt).all())

    return [
        BudgetStatus(
            category_id=b.category_id,
            budget=float(b.amount),
            spent=round(float(spent_by_category.get(b.category_id, 0)), 2),
            percentage=round(
                float(spent_by_category.get(b.category_id, 0)) / float(b.amount) * 100,
                1,
            ),
        )
        for b in budgets
    ]


@router.post("", status_code=201)
def create_budget(
    payload: BudgetCreate, db: DbDep, user: CurrentUserDep
) -> BudgetOut:
    household_id = _household_id(user)
    _get_expense_category(db, household_id, payload.category_id)
    existing = db.scalar(
        select(Budget).where(
            Budget.household_id == household_id,
            Budget.category_id == payload.category_id,
        )
    )
    if existing is not None:
        raise HTTPException(
            status_code=409, detail="Ya existe un presupuesto para esta categoría"
        )
    budget = Budget(
        household_id=household_id,
        category_id=payload.category_id,
        amount=payload.amount,
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
    db.commit()
    db.refresh(budget)
    return _budget_out(budget)


@router.delete("/{budget_id}", status_code=204)
def delete_budget(budget_id: str, db: DbDep, user: CurrentUserDep) -> None:
    household_id = _household_id(user)
    budget = _get_budget(db, household_id, budget_id)
    db.delete(budget)
    db.commit()
