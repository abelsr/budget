from datetime import date, datetime, timezone
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import extract, func, select

from app.api.deps import CurrentUserDep, DbDep
from app.models import Transaction
from app.schemas.summary import (
    CategoryTotal,
    MonthSummaryResponse,
    RangeMonthTotal,
    RangeSummaryResponse,
)
from app.services.recurring import materialize_due

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

    materialize_due(db, user.household_id)

    if month is None:
        now = _now()
        year, month_num = now.year, now.month
    else:
        year, month_num = int(month[:4]), int(month[5:7])
        if not 1 <= month_num <= 12:
            raise HTTPException(status_code=422, detail="Mes inválido")

    base_filter = [
        Transaction.household_id == user.household_id,
        extract("year", Transaction.date) == year,
        extract("month", Transaction.date) == month_num,
    ]

    def _sum(tx_type: str) -> float:
        stmt = select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            *base_filter, Transaction.type == tx_type
        )
        return round(float(db.scalar(stmt)), 2)

    income = _sum("income")
    expense = _sum("expense")

    by_category_stmt = (
        select(Transaction.category_id, func.sum(Transaction.amount))
        .where(*base_filter, Transaction.type == "expense")
        .group_by(Transaction.category_id)
        .order_by(func.sum(Transaction.amount).desc())
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

    materialize_due(db, user.household_id)
    rows = db.execute(
        select(Transaction.date, Transaction.type, Transaction.amount, Transaction.category_id).where(
            Transaction.household_id == user.household_id,
            Transaction.date >= from_date,
            Transaction.date <= to_date,
        )
    ).all()

    monthly_totals: dict[str, dict[str, float]] = {}
    category_totals: dict[str, float] = {}
    for tx_date, tx_type, amount, category_id in rows:
        month = tx_date.strftime("%Y-%m")
        totals = monthly_totals.setdefault(month, {"income": 0.0, "expense": 0.0})
        totals[tx_type] += float(amount)
        if tx_type == "expense":
            category_totals[category_id] = category_totals.get(category_id, 0.0) + float(amount)

    monthly = [
        RangeMonthTotal(
            month=month,
            income=round(totals["income"], 2),
            expense=round(totals["expense"], 2),
            net=round(totals["income"] - totals["expense"], 2),
        )
        for month, totals in sorted(monthly_totals.items())
    ]
    by_category = [
        CategoryTotal(category_id=category_id, total=round(total, 2))
        for category_id, total in sorted(category_totals.items(), key=lambda item: item[1], reverse=True)
    ]
    return RangeSummaryResponse(monthly=monthly, by_category=by_category)
