from datetime import date
from decimal import Decimal, ROUND_CEILING

from fastapi import APIRouter, HTTPException
from sqlalchemy import select, update

from app.api.deps import CurrentUserDep, DbDep
from app.models import Account, SavingsGoal, User
from app.schemas.goals import (
    MAX_MONEY,
    SavingsGoalContribution,
    SavingsGoalCreate,
    SavingsGoalOut,
    SavingsGoalUpdate,
)

router = APIRouter(prefix="/goals", tags=["goals"])


def _household_id(user: User) -> str:
    if user.household_id is None:
        raise HTTPException(status_code=400, detail="El usuario no pertenece a un hogar")
    return user.household_id


def _get_goal(db, household_id: str, goal_id: str) -> SavingsGoal:
    goal = db.get(SavingsGoal, goal_id)
    if goal is None or goal.household_id != household_id:
        raise HTTPException(status_code=404, detail="Meta no encontrada")
    return goal


def _validate_account(db, household_id: str, account_id: str | None) -> None:
    if account_id is None:
        return
    account = db.get(Account, account_id)
    if account is None or account.household_id != household_id or account.owner_id is not None:
        raise HTTPException(status_code=422, detail="Cuenta compartida no encontrada")


def _goal_out(goal: SavingsGoal) -> SavingsGoalOut:
    target = Decimal(goal.target_amount)
    current = Decimal(goal.current_amount)
    remaining = max(Decimal("0"), target - current)
    completed = current >= target
    status = "none"
    required_monthly_contribution = None
    if not goal.archived and not completed and goal.target_date is not None:
        if goal.plan_paused:
            status = "paused"
        elif goal.target_date < date.today():
            status = "overdue"
        else:
            status = "active"
            months = (goal.target_date.year - date.today().year) * 12 + goal.target_date.month - date.today().month + 1
            required_monthly_contribution = float(
                (remaining / months).quantize(Decimal("0.0001"), rounding=ROUND_CEILING)
            )
    return SavingsGoalOut(
        id=goal.id,
        household_id=goal.household_id,
        name=goal.name,
        target_amount=float(target),
        current_amount=float(current),
        target_date=goal.target_date,
        account_id=goal.account_id,
        icon=goal.icon,
        color=goal.color,
        archived=goal.archived,
        progress_pct=min(100, round(float(current / target * 100), 1)),
        remaining=round(float(remaining), 2),
        is_completed=completed,
        plan_paused=goal.plan_paused,
        plan_status=status,
        required_monthly_contribution=required_monthly_contribution,
    )


@router.get("")
def list_goals(db: DbDep, user: CurrentUserDep) -> list[SavingsGoalOut]:
    household_id = _household_id(user)
    goals = db.scalars(
        select(SavingsGoal)
        .where(SavingsGoal.household_id == household_id)
        .order_by(SavingsGoal.archived, SavingsGoal.created_at, SavingsGoal.id)
    ).all()
    return [_goal_out(goal) for goal in goals]


@router.post("", status_code=201)
def create_goal(
    payload: SavingsGoalCreate, db: DbDep, user: CurrentUserDep
) -> SavingsGoalOut:
    household_id = _household_id(user)
    _validate_account(db, household_id, payload.account_id)
    goal = SavingsGoal(household_id=household_id, **payload.model_dump())
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return _goal_out(goal)


@router.patch("/{goal_id}")
def update_goal(
    goal_id: str, payload: SavingsGoalUpdate, db: DbDep, user: CurrentUserDep
) -> SavingsGoalOut:
    household_id = _household_id(user)
    goal = _get_goal(db, household_id, goal_id)
    data = payload.model_dump(exclude_unset=True)
    if "account_id" in data:
        _validate_account(db, household_id, data["account_id"])
    for field, value in data.items():
        setattr(goal, field, value)
    db.commit()
    db.refresh(goal)
    return _goal_out(goal)


@router.post("/{goal_id}/contribute")
def contribute_to_goal(
    goal_id: str, payload: SavingsGoalContribution, db: DbDep, user: CurrentUserDep
) -> SavingsGoalOut:
    household_id = _household_id(user)
    _get_goal(db, household_id, goal_id)
    # Do the increment in SQL so simultaneous contributions cannot overwrite each other.
    result = db.execute(
        update(SavingsGoal)
        .where(
            SavingsGoal.id == goal_id,
            SavingsGoal.household_id == household_id,
            SavingsGoal.current_amount + payload.amount <= MAX_MONEY,
            SavingsGoal.current_amount + payload.amount >= -MAX_MONEY,
        )
        .values(current_amount=SavingsGoal.current_amount + payload.amount)
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=422, detail="El aporte excede el límite permitido")
    db.commit()
    return _goal_out(_get_goal(db, household_id, goal_id))


@router.delete("/{goal_id}", status_code=204)
def delete_goal(goal_id: str, db: DbDep, user: CurrentUserDep) -> None:
    household_id = _household_id(user)
    db.delete(_get_goal(db, household_id, goal_id))
    db.commit()
