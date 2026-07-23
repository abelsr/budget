from fastapi import APIRouter, HTTPException
from sqlalchemy import func, select

from app.api.deps import CurrentUserDep, DbDep
from app.models import Account, Transaction, User
from app.schemas.accounts import AccountCreate, AccountOut, AccountUpdate

router = APIRouter(prefix="/accounts", tags=["accounts"])


def _household_id(user: User) -> str:
    if user.household_id is None:
        raise HTTPException(status_code=400, detail="El usuario no pertenece a un hogar")
    return user.household_id


def _get_account(db, household_id: str, account_id: str) -> Account:
    account = db.get(Account, account_id)
    if account is None or account.household_id != household_id:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")
    return account


def _account_out(account: Account, balance: float) -> AccountOut:
    return AccountOut(
        id=account.id,
        household_id=account.household_id,
        name=account.name,
        kind=account.kind,
        balance=round(balance, 2),
    )


@router.get("")
def list_accounts(db: DbDep, user: CurrentUserDep) -> list[AccountOut]:
    household_id = _household_id(user)
    accounts = db.scalars(
        select(Account)
        .where(Account.household_id == household_id)
        .order_by(Account.created_at, Account.id)
    ).all()
    totals = db.execute(
        select(Transaction.account_id, Transaction.type, func.sum(Transaction.amount))
        .where(Transaction.household_id == household_id)
        .group_by(Transaction.account_id, Transaction.type)
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
            - sums.get("expense", 0.0)
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
    account = _get_account(db, household_id, account_id)
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(account, field, value)
    db.commit()
    db.refresh(account)
    totals = db.execute(
        select(Transaction.type, func.sum(Transaction.amount))
        .where(Transaction.account_id == account.id)
        .group_by(Transaction.type)
    ).all()
    sums = {tx_type: float(total or 0) for tx_type, total in totals}
    balance = (
        float(account.opening_balance) + sums.get("income", 0.0) - sums.get("expense", 0.0)
    )
    return _account_out(account, balance)


@router.delete("/{account_id}", status_code=204)
def delete_account(account_id: str, db: DbDep, user: CurrentUserDep) -> None:
    household_id = _household_id(user)
    account = _get_account(db, household_id, account_id)
    has_movements = db.scalar(
        select(func.count())
        .select_from(Transaction)
        .where(Transaction.account_id == account.id)
    )
    if has_movements:
        raise HTTPException(status_code=409, detail="La cuenta tiene movimientos")
    db.delete(account)
    db.commit()
