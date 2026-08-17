from datetime import date

from fastapi import APIRouter, HTTPException
from sqlalchemy import func, select, update

from app.api.deps import CurrentUserDep, DbDep
from app.models import Account, Household, InstalmentPlan, RecurringRule, SavingsGoal, Transaction, User
from app.schemas.accounts import AccountCreate, AccountOut, AccountUpdate
from app.services.account_access import can_operate, visible_accounts
from app.services.account_balances import account_balance, balance_sums
from app.services.card_calendar import last_statement_date, next_statement_date, payment_due_date
from app.services.recurring import materialize_due

router = APIRouter(prefix="/accounts", tags=["accounts"])


def _household_id(user: User) -> str:
    if user.household_id is None:
        raise HTTPException(status_code=400, detail="El usuario no pertenece a un hogar")
    return user.household_id


def _get_account(db, household_id: str, user_id: str, account_id: str) -> Account:
    account = db.get(Account, account_id)
    if account is None or account.household_id != household_id or not can_operate(account, user_id):
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")
    return account


def _card_dates(account: Account, today: date) -> tuple[str | None, str | None, str | None]:
    """(last_statement, next_statement, next_payment_due) as ISO strings."""
    if account.kind != "credit" or account.statement_day is None or account.payment_due_days is None:
        return (None, None, None)
    nxt = next_statement_date(account.statement_day, today)
    return (
        last_statement_date(account.statement_day, today).isoformat(),
        nxt.isoformat(),
        payment_due_date(nxt, account.payment_due_days).isoformat(),
    )


def _account_out(account: Account, balance: float, today: date | None = None) -> AccountOut:
    last_statement, next_statement, next_due = _card_dates(account, today or date.today())
    return AccountOut(
        id=account.id,
        household_id=account.household_id,
        name=account.name,
        kind=account.kind,
        opening_balance=float(account.opening_balance),
        balance=round(balance, 2),
        bank=account.bank,
        card_brand=account.card_brand,
        last_four=account.last_four,
        is_personal=account.owner_id is not None,
        statement_day=account.statement_day,
        payment_due_days=account.payment_due_days,
        last_statement_date=last_statement,
        next_statement_date=next_statement,
        next_payment_due_date=next_due,
    )


@router.get("")
def list_accounts(db: DbDep, user: CurrentUserDep) -> list[AccountOut]:
    household_id = _household_id(user)
    # El Dashboard dispara cuentas, movimientos y resumen en paralelo: si solo
    # materializara el de movimientos, los saldos saldrían desfasados en la
    # primera carga después de que una regla vence.
    materialize_due(db, household_id, user.id)
    accounts = db.scalars(
        select(Account)
        .where(Account.household_id == household_id, visible_accounts(user.id))
        .order_by(Account.created_at, Account.id)
    ).all()
    account_sums = balance_sums(db, household_id, visible_accounts(user.id))
    result = []
    for account in accounts:
        balance = account_balance(account.opening_balance, account_sums.get(account.id, {}))
        result.append(_account_out(account, balance))
    return result


@router.post("", status_code=201)
def create_account(
    payload: AccountCreate, db: DbDep, user: CurrentUserDep
) -> AccountOut:
    household_id = _household_id(user)
    if (payload.statement_day is not None or payload.payment_due_days is not None) and payload.kind != "credit":
        raise HTTPException(status_code=422, detail="Las fechas de ciclo solo aplican a cuentas de tarjeta de crédito")
    account = Account(
        household_id=household_id,
        name=payload.name,
        kind=payload.kind,
        opening_balance=payload.opening_balance,
        bank=payload.bank,
        card_brand=payload.card_brand,
        last_four=payload.last_four,
        owner_id=user.id if payload.is_personal else None,
        statement_day=payload.statement_day,
        payment_due_days=payload.payment_due_days,
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return _account_out(account, float(account.opening_balance))


@router.patch("/{account_id}")
def update_account(
    account_id: str, payload: AccountUpdate, db: DbDep, user: CurrentUserDep
) -> AccountOut:
    household_id = _household_id(user)
    account = _get_account(db, household_id, user.id, account_id)
    data = payload.model_dump(exclude_unset=True)
    is_personal = data.pop("is_personal", None)
    # After this update, a non-credit account must not keep cycle dates.
    effective_kind = data.get("kind") or account.kind
    if effective_kind != "credit":
        next_statement_day = data.get("statement_day", account.statement_day)
        next_payment_due_days = data.get("payment_due_days", account.payment_due_days)
        if next_statement_day is not None or next_payment_due_days is not None:
            raise HTTPException(status_code=422, detail="Las fechas de ciclo solo aplican a cuentas de tarjeta de crédito")
    if is_personal is True and account.owner_id is None:
        household = db.get(Household, household_id)
        if household is None or household.owner_id != user.id:
            raise HTTPException(status_code=403, detail="Solo la persona propietaria del hogar puede convertir una cuenta compartida en personal")
        if db.scalar(
            select(RecurringRule.id)
            .where(
                RecurringRule.account_id == account.id,
                RecurringRule.created_by_id != user.id,
            )
            .limit(1)
        ):
            raise HTTPException(
                status_code=409,
                detail="La cuenta tiene reglas recurrentes de otras personas",
            )
        if db.scalar(select(SavingsGoal.id).where(SavingsGoal.account_id == account.id).limit(1)):
            raise HTTPException(status_code=409, detail="La cuenta está vinculada a una meta del hogar")
        account.owner_id = user.id
    elif is_personal is False and account.owner_id is not None:
        if account.owner_id != user.id:
            raise HTTPException(status_code=403, detail="Solo la persona propietaria de la cuenta puede convertirla en compartida")
        account.owner_id = None
    for field, value in data.items():
        setattr(account, field, value)
    db.commit()
    db.refresh(account)
    sums = balance_sums(db, household_id, Account.id == account.id).get(account.id, {})
    return _account_out(account, account_balance(account.opening_balance, sums))


@router.delete("/{account_id}", status_code=204)
def delete_account(account_id: str, db: DbDep, user: CurrentUserDep) -> None:
    household_id = _household_id(user)
    account = _get_account(db, household_id, user.id, account_id)
    has_movements = db.scalar(
        select(func.count())
        .select_from(Transaction)
        .where(Transaction.account_id == account.id)
    )
    if has_movements:
        raise HTTPException(status_code=409, detail="La cuenta tiene movimientos")
    has_rules = db.scalar(
        select(RecurringRule.id).where(RecurringRule.account_id == account.id).limit(1)
    )
    if has_rules:
        raise HTTPException(status_code=409, detail="La cuenta tiene reglas recurrentes")
    # Defensive: a purchase (even soft-deleted) already blocks deletion with
    # "tiene movimientos"; this keeps the guard if that check ever narrows.
    has_plans = db.scalar(
        select(InstalmentPlan.id)
        .where(InstalmentPlan.account_id == account.id, InstalmentPlan.status.in_(["active", "paused"]))
        .limit(1)
    )
    if has_plans:
        raise HTTPException(status_code=409, detail="La cuenta tiene planes de instalados activos")
    # SQLite test databases do not enforce foreign keys; production's FK also
    # has ON DELETE SET NULL, so a goal always survives account deletion.
    db.execute(
        update(SavingsGoal)
        .where(SavingsGoal.account_id == account.id)
        .values(account_id=None)
    )
    db.delete(account)
    db.commit()
