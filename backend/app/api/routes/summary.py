from datetime import date, datetime, timezone
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import extract, func, select

from app.api.deps import CurrentUserDep, DbDep
from app.models import Account, Transaction, TransactionSplit
from app.schemas.summary import (
    CategoryTotal,
    MonthSummaryResponse,
    RangeSummaryResponse,
)
from app.services.recurring import materialize_due
from app.services.range_summary import build_range_report
from app.services.account_access import shared_accounts

router = APIRouter(prefix="/summary", tags=["summary"])

_MONTH_PATTERN = r"^\d{4}-\d{2}$"


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


@router.get("/month", response_model=MonthSummaryResponse)
def get_month_summary(
    db: DbDep,
    user: CurrentUserDep,
    month: Annotated[str | None, Query(pattern=_MONTH_PATTERN)] = None,
) -> MonthSummaryResponse:
    if user.household_id is None:
        raise HTTPException(status_code=400, detail="El usuario no pertenece a un hogar")

    materialize_due(db, user.household_id, user.id)

    if month is None:
        now = _now()
        year, month_num = now.year, now.month
    else:
        year, month_num = int(month[:4]), int(month[5:7])
        if not 1 <= month_num <= 12:
            raise HTTPException(status_code=422, detail="Mes inválido")

    base_filter = [
        Transaction.household_id == user.household_id,
        Transaction.deleted_at.is_(None),
        shared_accounts(),
        extract("year", Transaction.date) == year,
        extract("month", Transaction.date) == month_num,
    ]

    def _sum(tx_type: str) -> float:
        stmt = select(func.coalesce(func.sum(Transaction.amount), 0)).join(Account).where(
            *base_filter, Transaction.type == tx_type
        )
        return round(float(db.scalar(stmt)), 2)

    income = _sum("income")
    expense = _sum("expense")

    # A parent movement contributes to account totals once, while its split
    # allocations contribute to their individual category totals.
    by_category_stmt = (
        select(TransactionSplit.category_id, func.sum(TransactionSplit.amount).label("total"))
        .join(Transaction, Transaction.id == TransactionSplit.transaction_id)
        .join(Account, Account.id == Transaction.account_id)
        .where(*base_filter, Transaction.type == "expense", Transaction.is_split.is_(True))
        .group_by(TransactionSplit.category_id)
        .union_all(
            select(Transaction.category_id, func.sum(Transaction.amount).label("total")).join(Account)
            .where(*base_filter, Transaction.type == "expense", Transaction.is_split.is_(False))
            .group_by(Transaction.category_id)
        )
        .subquery()
    )
    by_category_stmt = (
        select(by_category_stmt.c.category_id, func.sum(by_category_stmt.c.total))
        .group_by(by_category_stmt.c.category_id)
        .order_by(func.sum(by_category_stmt.c.total).desc())
    )
    by_category = [
        CategoryTotal(category_id=category_id, total=round(float(total), 2))
        for category_id, total in db.execute(by_category_stmt).all()
    ]

    return MonthSummaryResponse(income=income, expense=expense, by_category=by_category)


@router.get("/range", response_model=RangeSummaryResponse)
def get_range_summary(
    db: DbDep,
    user: CurrentUserDep,
    from_date: Annotated[date, Query(alias="from")],
    to_date: Annotated[date, Query(alias="to")],
) -> RangeSummaryResponse:
    if user.household_id is None:
        raise HTTPException(status_code=400, detail="El usuario no pertenece a un hogar")
    if from_date > to_date:
        raise HTTPException(status_code=422, detail="La fecha inicial debe ser anterior a la final")

    materialize_due(db, user.household_id, user.id)
    report = build_range_report(db, user.household_id, from_date, to_date)
    return RangeSummaryResponse(monthly=report.monthly, by_category=report.by_category)
