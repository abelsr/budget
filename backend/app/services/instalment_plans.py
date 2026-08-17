"""MSI instalment plan lifecycle.

Advisory like goal plans: the plan itself never creates ledger movements,
except the explicit cash->card transfer when the user records a payment
through `mark_paid(source_account_id=...)`.
"""

from datetime import date

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Account, InstalmentPlan, Transaction, TransferGroup
from app.services.account_access import can_operate
from app.services.card_calendar import instalment_schedule, next_unpaid_due

ACTIVE_STATUSES = ("active", "paused")


def get_plan_or_404(db: Session, household_id: str, plan_id: str) -> InstalmentPlan:
    plan = db.get(InstalmentPlan, plan_id)
    if plan is None or plan.household_id != household_id:
        raise HTTPException(status_code=404, detail="Plan no encontrado")
    return plan


def active_plan_for(db: Session, transaction_id: str) -> InstalmentPlan | None:
    """Active or paused plan bound to a purchase; None when there is none."""
    return db.scalar(
        select(InstalmentPlan).where(
            InstalmentPlan.source_transaction_id == transaction_id,
            InstalmentPlan.status.in_(ACTIVE_STATUSES),
        )
    )


def create_plan(
    db: Session,
    *,
    household_id: str,
    user_id: str,
    source_transaction_id: str,
    months: int,
    first_due_date: date,
) -> InstalmentPlan:
    exists = db.scalar(
        select(InstalmentPlan.id).where(
            InstalmentPlan.household_id == household_id,
            InstalmentPlan.source_transaction_id == source_transaction_id,
        )
    )
    if exists is not None:
        raise HTTPException(status_code=409, detail="Esta compra ya tiene un plan de instalados")
    purchase = db.scalar(
        select(Transaction).where(
            Transaction.id == source_transaction_id,
            Transaction.household_id == household_id,
            Transaction.deleted_at.is_(None),
        )
    )
    if purchase is None:
        raise HTTPException(status_code=404, detail="Movimiento no encontrado")
    if purchase.type != "expense" or purchase.category_id is None:
        raise HTTPException(status_code=422, detail="Solo una compra (gasto) puede tener un plan de instalados")
    account = db.get(Account, purchase.account_id)
    if account is None or account.household_id != household_id or account.kind != "credit":
        raise HTTPException(status_code=422, detail="El plan requiere una compra en una cuenta de tarjeta de crédito")
    if account.owner_id is not None:
        raise HTTPException(status_code=422, detail="El plan requiere una cuenta compartida del hogar")
    if first_due_date < date.today():
        raise HTTPException(status_code=422, detail="La primera fecha de pago no puede estar en el pasado")
    total = round(float(purchase.amount), 4)
    plan = InstalmentPlan(
        household_id=household_id,
        account_id=account.id,
        source_transaction_id=purchase.id,
        months=months,
        total_amount=total,
        monthly_amount=round(total / months, 4),
        first_due_date=first_due_date,
        created_by_id=user_id,
    )
    db.add(plan)
    db.flush()
    return plan


def plan_out(plan: InstalmentPlan, account_name: str) -> dict:
    nxt = next_unpaid_due(plan)
    return {
        "id": plan.id,
        "household_id": plan.household_id,
        "account_id": plan.account_id,
        "account_name": account_name,
        "source_transaction_id": plan.source_transaction_id,
        "months": plan.months,
        "total_amount": float(plan.total_amount),
        "monthly_amount": float(plan.monthly_amount),
        "first_due_date": plan.first_due_date,
        "paid_count": plan.paid_count,
        "status": plan.status,
        "next_due_date": nxt[0] if nxt else None,
        "next_due_amount": round(nxt[1], 2) if nxt else None,
        "schedule": [
            {"date": due, "amount": round(amount, 4), "paid": index < plan.paid_count}
            for index, (due, amount) in enumerate(instalment_schedule(plan))
        ],
        "created_at": plan.created_at,
    }


def mark_paid(
    db: Session,
    plan: InstalmentPlan,
    *,
    user_id: str,
    source_account_id: str | None = None,
    payment_date: date | None = None,
) -> None:
    if plan.status != "active":
        raise HTTPException(status_code=409, detail=f"El plan está {plan.status}")
    if plan.paid_count >= plan.months:
        raise HTTPException(status_code=409, detail="El plan ya está completado")
    if source_account_id is not None:
        _create_payment_transfer(
            db, plan=plan, user_id=user_id,
            source_account_id=source_account_id, payment_date=payment_date or date.today(),
        )
    plan.paid_count += 1
    if plan.paid_count == plan.months:
        plan.status = "completed"


def _create_payment_transfer(
    db: Session, *, plan: InstalmentPlan, user_id: str, source_account_id: str, payment_date: date
) -> None:
    source = db.get(Account, source_account_id)
    card = db.get(Account, plan.account_id)
    if source is None or source.household_id != plan.household_id or source.id == card.id:
        raise HTTPException(status_code=422, detail="Elige una cuenta de origen distinta de la tarjeta")
    if source.owner_id is not None or not can_operate(source, user_id):
        raise HTTPException(status_code=422, detail="La cuenta de origen debe ser compartida del hogar")
    amount = instalment_schedule(plan)[plan.paid_count][1]
    group = TransferGroup(household_id=plan.household_id, client_id=None, created_by_id=user_id)
    db.add(group)
    db.flush()
    note = f"Instalado {plan.paid_count + 1}/{plan.months}"
    outgoing = Transaction(
        household_id=plan.household_id, type="transfer", amount=amount,
        account_id=source.id, member_id=user_id, date=payment_date,
        note=note, transfer_group_id=group.id, transfer_direction="outflow",
    )
    incoming = Transaction(
        household_id=plan.household_id, type="transfer", amount=amount,
        account_id=card.id, member_id=user_id, date=payment_date,
        note=note, transfer_group_id=group.id, transfer_direction="inflow",
    )
    db.add_all([outgoing, incoming])


def set_status(db: Session, plan: InstalmentPlan, status: str) -> None:
    if plan.status not in ACTIVE_STATUSES:
        raise HTTPException(status_code=409, detail=f"El plan está {plan.status}")
    plan.status = status
