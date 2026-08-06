from fastapi import APIRouter, HTTPException
from sqlalchemy import func, select, update

from app.api.deps import CurrentUserDep, DbDep
from app.models import Account, Household, RecurringRule, SavingsGoal, Transaction, User
from app.schemas.accounts import AccountCreate, AccountOut, AccountUpdate
from app.services.account_access import can_operate, visible_accounts
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


def _account_out(account: Account, balance: float) -> AccountOut:
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
    totals = db.execute(
        select(Transaction.account_id, func.coalesce(Transaction.transfer_direction, Transaction.type), func.sum(Transaction.amount))
        .join(Account, Account.id == Transaction.account_id)
        .where(Transaction.household_id == household_id, visible_accounts(user.id))
        .group_by(Transaction.account_id, func.coalesce(Transaction.transfer_direction, Transaction.type))
    ).all()
    agg: dict[str, dict[str, float]] = {}
    for account_id, tx_type, total in totals:
        agg.setdefault(account_id, {})[tx_type] = float(total or 0)
    result = []
    for account in accounts:
        sums = agg.get(account.id, {})
        balance = (
            float(account.opening_balance)
            + sums.get("income", 0.0)
            + sums.get("inflow", 0.0)
            - sums.get("expense", 0.0)
            - sums.get("outflow", 0.0)
        )
        result.append(_account_out(account, balance))
    return result


@router.post("", status_code=201)
def create_account(
    payload: AccountCreate, db: DbDep, user: CurrentUserDep
) -> AccountOut:
    household_id = _household_id(user)
    account = Account(
        household_id=household_id,
        name=payload.name,
        kind=payload.kind,
        opening_balance=payload.opening_balance,
        bank=payload.bank,
        card_brand=payload.card_brand,
        last_four=payload.last_four,
        owner_id=user.id if payload.is_personal else None,
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
    totals = db.execute(
        select(func.coalesce(Transaction.transfer_direction, Transaction.type), func.sum(Transaction.amount))
        .where(Transaction.account_id == account.id)
        .group_by(func.coalesce(Transaction.transfer_direction, Transaction.type))
    ).all()
    sums = {tx_type: float(total or 0) for tx_type, total in totals}
    balance = (
        float(account.opening_balance)
        + sums.get("income", 0.0)
        + sums.get("inflow", 0.0)
        - sums.get("expense", 0.0)
        - sums.get("outflow", 0.0)
    )
    return _account_out(account, balance)


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
    # SQLite test databases do not enforce foreign keys; production's FK also
    # has ON DELETE SET NULL, so a goal always survives account deletion.
    db.execute(
        update(SavingsGoal)
        .where(SavingsGoal.account_id == account.id)
        .values(account_id=None)
    )
    db.delete(account)
    db.commit()
