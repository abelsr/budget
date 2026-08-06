from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Account, Category, Transaction, User
from app.schemas.summary import CategoryTotal, RangeMonthTotal
from app.services.account_access import shared_accounts


@dataclass
class LedgerTransaction:
    date: date
    type: str
    amount: float
    category: str
    account: str
    member: str
    note: str | None


@dataclass
class RangeReport:
    monthly: list[RangeMonthTotal]
    by_category: list[CategoryTotal]
    category_names: dict[str, str]
    transactions: list[LedgerTransaction]


def build_range_report(
    db: Session, household_id: str, from_date: date, to_date: date
) -> RangeReport:
    """Build the common range data used by the JSON summary and file exports."""
    rows = db.execute(
        select(
            Transaction.date,
            Transaction.type,
            Transaction.amount,
            Transaction.category_id,
            Category.name,
            Account.name,
            User.name,
            Transaction.note,
        )
        .join(Category, Category.id == Transaction.category_id)
        .join(Account, Account.id == Transaction.account_id)
        .join(User, User.id == Transaction.member_id)
        .where(
            Transaction.household_id == household_id,
            Transaction.deleted_at.is_(None),
            shared_accounts(),
            Transaction.type.in_(["income", "expense"]),
            Transaction.date >= from_date,
            Transaction.date <= to_date,
        )
        .order_by(Transaction.date, Transaction.id)
    ).all()

    monthly_totals: dict[str, dict[str, float]] = {}
    category_totals: dict[str, float] = {}
    category_names: dict[str, str] = {}
    transactions = []
    for tx_date, tx_type, amount, category_id, category, account, member, note in rows:
        amount_float = float(amount)
        month = tx_date.strftime("%Y-%m")
        totals = monthly_totals.setdefault(month, {"income": 0.0, "expense": 0.0})
        totals[tx_type] += amount_float
        if tx_type == "expense":
            category_totals[category_id] = category_totals.get(category_id, 0.0) + amount_float
            category_names[category_id] = category
        transactions.append(
            LedgerTransaction(tx_date, tx_type, amount_float, category, account, member, note)
        )

    return RangeReport(
        monthly=[
            RangeMonthTotal(
                month=month,
                income=round(totals["income"], 2),
                expense=round(totals["expense"], 2),
                net=round(totals["income"] - totals["expense"], 2),
            )
            for month, totals in sorted(monthly_totals.items())
        ],
        by_category=[
            CategoryTotal(category_id=category_id, total=round(total, 2))
            for category_id, total in sorted(
                category_totals.items(), key=lambda item: item[1], reverse=True
            )
        ],
        category_names=category_names,
        transactions=transactions,
    )
