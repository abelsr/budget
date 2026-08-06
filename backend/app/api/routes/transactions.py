from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select

from app.api.deps import CurrentUserDep, DbDep
from app.models import Account, Category, RecurringRule, Transaction, User
from app.schemas.transactions import (
    TransactionCreate,
    TransactionOut,
    TransactionUpdate,
)
from app.services.recurring import advance, materialize_due

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
        author_name=tx.author.name,
        date=tx.date,
        note=tx.note,
        recurring_rule_id=tx.recurring_rule_id,
        attachments=tx.attachments,
    )


@router.get("")
def list_transactions(
    db: DbDep,
    user: CurrentUserDep,
    limit: Annotated[int, Query(le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    month: Annotated[str | None, Query(pattern=_MONTH_PATTERN)] = None,
    q: Annotated[str | None, Query(max_length=200)] = None,
    category_id: Annotated[str | None, Query(alias="categoryId")] = None,
    account_id: Annotated[str | None, Query(alias="accountId")] = None,
    member_id: Annotated[str | None, Query(alias="memberId")] = None,
    transaction_type: Annotated[Literal["expense", "income"] | None, Query(alias="type")] = None,
    from_date: Annotated[date | None, Query(alias="from")] = None,
    to_date: Annotated[date | None, Query(alias="to")] = None,
) -> list[TransactionOut]:
    household_id = _household_id(user)
    materialize_due(db, household_id)
    stmt = select(Transaction).where(Transaction.household_id == household_id)
    if month is not None and (from_date is not None or to_date is not None):
        raise HTTPException(
            status_code=422,
            detail="month no se puede combinar con from ni to",
        )
    if month is not None:
        year, mon = int(month[:4]), int(month[5:7])
        if not 1 <= mon <= 12:
            raise HTTPException(status_code=422, detail="Mes inválido")
        start = date(year, mon, 1)
        end = date(year + 1, 1, 1) if mon == 12 else date(year, mon + 1, 1)
        stmt = stmt.where(Transaction.date >= start, Transaction.date < end)
    else:
        if from_date is not None and to_date is not None and from_date > to_date:
            raise HTTPException(status_code=422, detail="La fecha inicial debe ser anterior a la final")
        if from_date is not None:
            stmt = stmt.where(Transaction.date >= from_date)
        if to_date is not None:
            stmt = stmt.where(Transaction.date <= to_date)
    if q:
        stmt = stmt.where(Transaction.note.ilike(f"%{q}%"))
    if category_id is not None:
        stmt = stmt.where(Transaction.category_id == category_id)
    if account_id is not None:
        stmt = stmt.where(Transaction.account_id == account_id)
    if member_id is not None:
        stmt = stmt.where(Transaction.member_id == member_id)
    if transaction_type is not None:
        stmt = stmt.where(Transaction.type == transaction_type)
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
        member_id=user.id,  # El autor siempre es el usuario autenticado.
        date=payload.date,
        note=payload.note,
    )
    if payload.repeat is not None:
        from datetime import timedelta

        from app.services.recurring import MAX_BACKFILL_DAYS

        anchor_day = payload.date.day if payload.repeat == "monthly" else None
        next_run_date = advance(payload.date, payload.repeat, anchor_day)
        if next_run_date < date.today() - timedelta(days=MAX_BACKFILL_DAYS):
            raise HTTPException(
                status_code=422,
                detail="La próxima fecha no puede estar a más de un año en el pasado",
            )
        rule = RecurringRule(
            household_id=household_id,
            type=payload.type,
            amount=payload.amount,
            category_id=payload.category_id,
            account_id=payload.account_id,
            created_by_id=user.id,
            frequency=payload.repeat,
            # Esta transacción es la primera ocurrencia: la regla arranca en la
            # siguiente, o la materialización la duplicaría hoy mismo.
            next_run_date=next_run_date,
            anchor_day=anchor_day,
            note=payload.note,
        )
        db.add(rule)
        db.flush()  # el id se asigna al flush y hace falta para ligar
        tx.recurring_rule_id = rule.id
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
