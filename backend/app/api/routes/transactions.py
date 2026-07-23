from datetime import date
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select

from app.api.deps import CurrentUserDep, DbDep
from app.models import Account, Category, Transaction, User
from app.schemas.transactions import (
    TransactionCreate,
    TransactionOut,
    TransactionUpdate,
)

router = APIRouter(prefix="/transactions", tags=["transactions"])

_MONTH_PATTERN = r"^\d{4}-\d{2}$"


def _household_id(user: User) -> str:
    if user.household_id is None:
        raise HTTPException(status_code=400, detail="El usuario no pertenece a un hogar")
    return user.household_id


def _get_transaction(db, household_id: str, transaction_id: str) -> Transaction:
    tx = db.get(Transaction, transaction_id)
    if tx is None or tx.household_id != household_id:
        raise HTTPException(status_code=404, detail="Transacción no encontrada")
    return tx


def _validate_refs(db, household_id: str, category_id: str, account_id: str) -> None:
    category = db.get(Category, category_id)
    if category is None or category.household_id != household_id:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    account = db.get(Account, account_id)
    if account is None or account.household_id != household_id:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")


def _tx_out(tx: Transaction) -> TransactionOut:
    return TransactionOut(
        id=tx.id,
        household_id=tx.household_id,
        type=tx.type,
        amount=float(tx.amount),
        category_id=tx.category_id,
        account_id=tx.account_id,
        member_id=tx.member_id,
        date=tx.date,
        note=tx.note,
    )


@router.get("")
def list_transactions(
    db: DbDep,
    user: CurrentUserDep,
    limit: Annotated[int, Query(le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    month: Annotated[str | None, Query(pattern=_MONTH_PATTERN)] = None,
) -> list[TransactionOut]:
    household_id = _household_id(user)
    stmt = select(Transaction).where(Transaction.household_id == household_id)
    if month is not None:
        year, mon = int(month[:4]), int(month[5:7])
        if not 1 <= mon <= 12:
            raise HTTPException(status_code=422, detail="Mes inválido")
        start = date(year, mon, 1)
        end = date(year + 1, 1, 1) if mon == 12 else date(year, mon + 1, 1)
        stmt = stmt.where(Transaction.date >= start, Transaction.date < end)
    stmt = stmt.order_by(Transaction.date.desc(), Transaction.created_at.desc())
    stmt = stmt.limit(limit).offset(offset)
    transactions = db.scalars(stmt).all()
    return [_tx_out(tx) for tx in transactions]


@router.post("", status_code=201)
def create_transaction(
    payload: TransactionCreate, db: DbDep, user: CurrentUserDep
) -> TransactionOut:
    household_id = _household_id(user)
    _validate_refs(db, household_id, payload.category_id, payload.account_id)
    tx = Transaction(
        household_id=household_id,
        type=payload.type,
        amount=payload.amount,
        category_id=payload.category_id,
        account_id=payload.account_id,
        member_id=user.id,
        date=payload.date,
        note=payload.note,
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return _tx_out(tx)


@router.patch("/{transaction_id}")
def update_transaction(
    transaction_id: str, payload: TransactionUpdate, db: DbDep, user: CurrentUserDep
) -> TransactionOut:
    household_id = _household_id(user)
    tx = _get_transaction(db, household_id, transaction_id)
    data = payload.model_dump(exclude_unset=True)
    category_id = data.get("category_id", tx.category_id)
    account_id = data.get("account_id", tx.account_id)
    if "category_id" in data or "account_id" in data:
        _validate_refs(db, household_id, category_id, account_id)
    for field, value in data.items():
        setattr(tx, field, value)
    db.commit()
    db.refresh(tx)
    return _tx_out(tx)


@router.delete("/{transaction_id}", status_code=204)
def delete_transaction(transaction_id: str, db: DbDep, user: CurrentUserDep) -> None:
    household_id = _household_id(user)
    tx = _get_transaction(db, household_id, transaction_id)
    db.delete(tx)
    db.commit()
