from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select

from app.api.deps import CurrentUserDep, DbDep
from app.models import Account, InstalmentPlan, User
from app.schemas.instalment_plans import (
    InstalmentPlanCreate,
    InstalmentPlanOut,
    InstalmentPlanPay,
)
from app.services import instalment_plans as plans

router = APIRouter(prefix="/instalment-plans", tags=["instalment-plans"])


def _household_id(user: User) -> str:
    if user.household_id is None:
        raise HTTPException(status_code=400, detail="El usuario no pertenece a un hogar")
    return user.household_id


def _account_name(db, account_id: str) -> str:
    account = db.get(Account, account_id)
    return account.name if account is not None else ""


def _out(db, plan: InstalmentPlan) -> InstalmentPlanOut:
    return InstalmentPlanOut(**plans.plan_out(plan, _account_name(db, plan.account_id)))


@router.post("", status_code=201, response_model=InstalmentPlanOut)
def create_plan(
    payload: InstalmentPlanCreate, db: DbDep, user: CurrentUserDep
) -> InstalmentPlanOut:
    household_id = _household_id(user)
    plan = plans.create_plan(
        db,
        household_id=household_id,
        user_id=user.id,
        source_transaction_id=payload.source_transaction_id,
        months=payload.months,
        first_due_date=payload.first_due_date,
    )
    db.commit()
    return _out(db, plan)


@router.get("", response_model=list[InstalmentPlanOut])
def list_plans(
    db: DbDep,
    user: CurrentUserDep,
    source_transaction_id: Annotated[str | None, Query(alias="sourceTransactionId")] = None,
) -> list[InstalmentPlanOut]:
    household_id = _household_id(user)
    stmt = (
        select(InstalmentPlan, Account.name)
        .join(Account, Account.id == InstalmentPlan.account_id)
        .where(
            InstalmentPlan.household_id == household_id,
            InstalmentPlan.status.in_(("active", "paused")),
        )
    )
    if source_transaction_id is not None:
        # Issue #44: los detail sheets solo necesitan el plan (o no-plan) de
        # una transacción concreta, sin cargar toda la lista de planes.
        stmt = stmt.where(InstalmentPlan.source_transaction_id == source_transaction_id)
    plan_rows = db.execute(stmt.order_by(InstalmentPlan.first_due_date, InstalmentPlan.created_at)).all()
    return [InstalmentPlanOut(**plans.plan_out(plan, name)) for plan, name in plan_rows]


@router.get("/{plan_id}", response_model=InstalmentPlanOut)
def get_plan(plan_id: str, db: DbDep, user: CurrentUserDep) -> InstalmentPlanOut:
    plan = plans.get_plan_or_404(db, _household_id(user), plan_id)
    return _out(db, plan)


@router.post("/{plan_id}/pay", response_model=InstalmentPlanOut)
def pay_instalment(
    plan_id: str, payload: InstalmentPlanPay, db: DbDep, user: CurrentUserDep
) -> InstalmentPlanOut:
    household_id = _household_id(user)
    plan = plans.get_plan_or_404(db, household_id, plan_id)
    if payload.source_account_id is not None:
        # The payment transfer belongs to the household's shared accounts.
        source = db.get(Account, payload.source_account_id)
        if source is None or source.household_id != household_id:
            raise HTTPException(status_code=422, detail="Elige una cuenta de origen distinta de la tarjeta")
    plans.mark_paid(
        db, plan, user_id=user.id,
        source_account_id=payload.source_account_id, payment_date=payload.date,
    )
    db.commit()
    return _out(db, plan)


@router.post("/{plan_id}/pause", response_model=InstalmentPlanOut)
def pause_plan(plan_id: str, db: DbDep, user: CurrentUserDep) -> InstalmentPlanOut:
    plan = plans.get_plan_or_404(db, _household_id(user), plan_id)
    plans.set_status(db, plan, "paused")
    db.commit()
    return _out(db, plan)


@router.post("/{plan_id}/resume", response_model=InstalmentPlanOut)
def resume_plan(plan_id: str, db: DbDep, user: CurrentUserDep) -> InstalmentPlanOut:
    plan = plans.get_plan_or_404(db, _household_id(user), plan_id)
    plans.set_status(db, plan, "active")
    db.commit()
    return _out(db, plan)


@router.delete("/{plan_id}", status_code=204)
def cancel_plan(plan_id: str, db: DbDep, user: CurrentUserDep) -> None:
    plan = plans.get_plan_or_404(db, _household_id(user), plan_id)
    plans.set_status(db, plan, "cancelled")
    db.commit()
