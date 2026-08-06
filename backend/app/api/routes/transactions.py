from datetime import date
from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.deps import CurrentUserDep, DbDep
from app.models import Account, Category, RecurringRule, Transaction, TransferGroup, User
from app.schemas.transactions import (
    TransactionCreate,
    TransactionOut,
    TransactionUpdate,
)
from app.services.recurring import advance, materialize_due
from app.services.account_access import can_operate, visible_accounts

router = APIRouter(prefix="/transactions", tags=["transactions"])

_MONTH_PATTERN = r"^\d{4}-\d{2}$"


def _household_id(user: User) -> str:
    if user.household_id is None:
        raise HTTPException(status_code=400, detail="El usuario no pertenece a un hogar")
    return user.household_id


def _get_transaction(db, household_id: str, user_id: str, transaction_id: str) -> Transaction:
    tx = db.scalar(select(Transaction).join(Account).where(
        Transaction.id == transaction_id,
        Transaction.household_id == household_id,
        visible_accounts(user_id),
    ))
    if tx is None:
        raise HTTPException(status_code=404, detail="Transacción no encontrada")
    return tx


def _validate_refs(db, household_id: str, user_id: str, category_id: str, account_id: str) -> None:
    category = db.get(Category, category_id)
    if category is None or category.household_id != household_id or category.deleted:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    account = db.get(Account, account_id)
    if account is None or account.household_id != household_id or not can_operate(account, user_id):
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")


def _tx_out(tx: Transaction, db=None, user_id: str | None = None) -> TransactionOut:
    counterparty = None
    if tx.transfer_group_id and db is not None and user_id is not None:
        counterparty = db.scalar(
            select(Transaction)
            .where(
                Transaction.transfer_group_id == tx.transfer_group_id,
                Transaction.id != tx.id,
            )
            .limit(1)
        )
        if counterparty is not None:
            account = db.get(Account, counterparty.account_id)
            if account is None or not can_operate(account, user_id):
                counterparty = None
    return TransactionOut(
        id=tx.id,
        household_id=tx.household_id,
        client_id=tx.client_id,
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
        transfer_group_id=tx.transfer_group_id,
        transfer_direction=tx.transfer_direction,
        counterparty_account_id=counterparty.account_id if counterparty else None,
        counterparty_account_name=(db.get(Account, counterparty.account_id).name if counterparty else None),
    )


def _same_create_payload(tx: Transaction, payload: TransactionCreate, db) -> bool:
    """A client ID identifies one immutable create request, never a mutable draft."""
    if (
        tx.type != payload.type
        or _money(tx.amount) != _money(payload.amount)
        or tx.category_id != payload.category_id
        or tx.account_id != payload.account_id
        or tx.date != payload.date
        or tx.note != payload.note
    ):
        return False
    if payload.repeat is None:
        return tx.recurring_rule_id is None
    rule = db.get(RecurringRule, tx.recurring_rule_id)
    return rule is not None and rule.frequency == payload.repeat


def _money(value: Decimal | float) -> Decimal:
    """Compare amounts at the database's fixed four-decimal money scale."""
    return Decimal(str(value)).quantize(Decimal("0.0001"))


def _assert_replay_access(tx: Transaction, household_id: str, user_id: str, db) -> None:
    account = db.get(Account, tx.account_id)
    if account is None or account.household_id != household_id or not can_operate(account, user_id):
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")


def _validate_transfer_accounts(db, household_id: str, user_id: str, source_id: str, destination_id: str) -> tuple[Account, Account]:
    source = db.get(Account, source_id)
    destination = db.get(Account, destination_id)
    if (
        source is None
        or destination is None
        or source.household_id != household_id
        or destination.household_id != household_id
        or not can_operate(source, user_id)
        or not can_operate(destination, user_id)
    ):
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")
    if source.id == destination.id:
        raise HTTPException(status_code=422, detail="La cuenta origen y destino deben ser distintas")
    return source, destination


def _transfer_rows(db, group_id: str) -> list[Transaction]:
    rows = db.scalars(select(Transaction).where(Transaction.transfer_group_id == group_id)).all()
    if len(rows) != 2 or {row.transfer_direction for row in rows} != {"outflow", "inflow"}:
        raise HTTPException(status_code=409, detail="La transferencia está incompleta")
    if _money(rows[0].amount) != _money(rows[1].amount) or rows[0].account_id == rows[1].account_id:
        raise HTTPException(status_code=409, detail="La transferencia es inválida")
    return rows


def _same_transfer_payload(rows: list[Transaction], payload: TransactionCreate) -> bool:
    source = next(row for row in rows if row.transfer_direction == "outflow")
    destination = next(row for row in rows if row.transfer_direction == "inflow")
    return (
        _money(source.amount) == _money(payload.amount)
        and source.account_id == payload.source_account_id
        and destination.account_id == payload.destination_account_id
        and source.date == payload.date
        and source.note == payload.note
    )


def _assert_transfer_access(rows: list[Transaction], household_id: str, user_id: str, db) -> None:
    for row in rows:
        _assert_replay_access(row, household_id, user_id, db)


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
    transaction_type: Annotated[Literal["expense", "income", "transfer"] | None, Query(alias="type")] = None,
    include_transfers: Annotated[bool, Query(alias="includeTransfers")] = False,
    from_date: Annotated[date | None, Query(alias="from")] = None,
    to_date: Annotated[date | None, Query(alias="to")] = None,
) -> list[TransactionOut]:
    household_id = _household_id(user)
    materialize_due(db, household_id, user.id)
    stmt = select(Transaction).join(Account).where(Transaction.household_id == household_id, visible_accounts(user.id))
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
    elif not include_transfers:
        stmt = stmt.where(Transaction.type != "transfer")
    stmt = stmt.order_by(Transaction.date.desc(), Transaction.created_at.desc())
    stmt = stmt.limit(limit).offset(offset)
    transactions = db.scalars(stmt.execution_options(populate_existing=True)).all()
    return [_tx_out(tx, db, user.id) for tx in transactions]


@router.post("", status_code=201)
def create_transaction(
    payload: TransactionCreate, db: DbDep, user: CurrentUserDep
) -> TransactionOut:
    household_id = _household_id(user)
    client_id = str(payload.client_id) if payload.client_id is not None else None
    if payload.type == "transfer":
        assert payload.source_account_id is not None and payload.destination_account_id is not None
        if client_id is not None:
            existing_transaction = db.scalar(select(Transaction).where(
                Transaction.household_id == household_id,
                Transaction.client_id == client_id,
            ))
            if existing_transaction is not None:
                _assert_replay_access(existing_transaction, household_id, user.id, db)
                raise HTTPException(status_code=409, detail="El clientId ya se usó con un movimiento distinto")
            existing_group = db.scalar(select(TransferGroup).where(
                TransferGroup.household_id == household_id,
                TransferGroup.client_id == client_id,
            ))
            if existing_group is not None:
                rows = _transfer_rows(db, existing_group.id)
                _assert_transfer_access(rows, household_id, user.id, db)
                if not _same_transfer_payload(rows, payload):
                    raise HTTPException(status_code=409, detail="El clientId ya se usó con un movimiento distinto")
                return _tx_out(next(row for row in rows if row.transfer_direction == "outflow"), db, user.id)
        _validate_transfer_accounts(db, household_id, user.id, payload.source_account_id, payload.destination_account_id)
        group = TransferGroup(household_id=household_id, client_id=client_id, created_by_id=user.id)
        db.add(group)
        db.flush()
        outgoing = Transaction(
            household_id=household_id, type="transfer", amount=payload.amount,
            account_id=payload.source_account_id, member_id=user.id, date=payload.date,
            note=payload.note, transfer_group_id=group.id, transfer_direction="outflow",
        )
        incoming = Transaction(
            household_id=household_id, type="transfer", amount=payload.amount,
            account_id=payload.destination_account_id, member_id=user.id, date=payload.date,
            note=payload.note, transfer_group_id=group.id, transfer_direction="inflow",
        )
        db.add_all([outgoing, incoming])
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            if client_id is None:
                raise
            existing_group = db.scalar(select(TransferGroup).where(
                TransferGroup.household_id == household_id, TransferGroup.client_id == client_id,
            ))
            if existing_group is None:
                raise
            rows = _transfer_rows(db, existing_group.id)
            _assert_transfer_access(rows, household_id, user.id, db)
            if not _same_transfer_payload(rows, payload):
                raise HTTPException(status_code=409, detail="El clientId ya se usó con un movimiento distinto") from None
            return _tx_out(next(row for row in rows if row.transfer_direction == "outflow"), db, user.id)
        db.refresh(outgoing)
        return _tx_out(outgoing, db, user.id)
    if client_id is not None:
        existing_group = db.scalar(select(TransferGroup).where(
            TransferGroup.household_id == household_id,
            TransferGroup.client_id == client_id,
        ))
        if existing_group is not None:
            rows = _transfer_rows(db, existing_group.id)
            _assert_transfer_access(rows, household_id, user.id, db)
            raise HTTPException(status_code=409, detail="El clientId ya se usó con un movimiento distinto")
        existing = db.scalar(
            select(Transaction).where(
                Transaction.household_id == household_id,
                Transaction.client_id == client_id,
            )
        )
        if existing is not None:
            _assert_replay_access(existing, household_id, user.id, db)
            if not _same_create_payload(existing, payload, db):
                raise HTTPException(
                    status_code=409,
                    detail="El clientId ya se usó con un movimiento distinto",
                )
            return _tx_out(existing)
    assert payload.category_id is not None and payload.account_id is not None
    _validate_refs(db, household_id, user.id, payload.category_id, payload.account_id)
    tx = Transaction(
        household_id=household_id,
        client_id=client_id,
        type=payload.type,
        amount=payload.amount,
        category_id=payload.category_id,
        account_id=payload.account_id,
        member_id=user.id,  # El autor siempre es el usuario autenticado.
        date=payload.date,
        note=payload.note,
    )
    # Flush the unique key before creating a recurrence. A concurrent retry can
    # then roll back to the savepoint without leaving a second rule behind.
    try:
        with db.begin_nested():
            db.add(tx)
            db.flush()
    except IntegrityError:
        if client_id is None:
            raise
        existing = db.scalar(
            select(Transaction).where(
                Transaction.household_id == household_id,
                Transaction.client_id == client_id,
            )
        )
        if existing is None:
            raise
        _assert_replay_access(existing, household_id, user.id, db)
        if not _same_create_payload(existing, payload, db):
            raise HTTPException(
                status_code=409,
                detail="El clientId ya se usó con un movimiento distinto",
            ) from None
        return _tx_out(existing)
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
    db.commit()
    db.refresh(tx)
    return _tx_out(tx)


@router.patch("/{transaction_id}")
def update_transaction(
    transaction_id: str, payload: TransactionUpdate, db: DbDep, user: CurrentUserDep
) -> TransactionOut:
    household_id = _household_id(user)
    tx = _get_transaction(db, household_id, user.id, transaction_id)
    if tx.type == "transfer":
        if tx.transfer_group_id is None:
            raise HTTPException(status_code=409, detail="La transferencia está incompleta")
        rows = _transfer_rows(db, tx.transfer_group_id)
        _assert_transfer_access(rows, household_id, user.id, db)
        data = payload.model_dump(exclude_unset=True)
        source = next(row for row in rows if row.transfer_direction == "outflow")
        destination = next(row for row in rows if row.transfer_direction == "inflow")
        source_id = data.pop("source_account_id", source.account_id)
        destination_id = data.pop("destination_account_id", destination.account_id)
        if "account_id" in data:
            raise HTTPException(status_code=422, detail="Usa cuenta origen y destino para editar una transferencia")
        if "category_id" in data or data.get("type") not in (None, "transfer"):
            raise HTTPException(status_code=422, detail="Una transferencia no usa categoría ni tipo de movimiento")
        _validate_transfer_accounts(db, household_id, user.id, source_id, destination_id)
        for row in rows:
            row.amount = data.get("amount", row.amount)
            row.date = data.get("date", row.date)
            row.note = data.get("note", row.note)
        source.account_id = source_id
        destination.account_id = destination_id
        db.commit()
        db.refresh(tx)
        return _tx_out(tx, db, user.id)
    data = payload.model_dump(exclude_unset=True)
    if data.get("type") == "transfer" or "source_account_id" in data or "destination_account_id" in data:
        raise HTTPException(status_code=422, detail="Una transacción existente no se puede convertir en transferencia")
    category_id = data.get("category_id", tx.category_id)
    account_id = data.get("account_id", tx.account_id)
    if "category_id" in data or "account_id" in data:
        _validate_refs(db, household_id, user.id, category_id, account_id)
    for field, value in data.items():
        setattr(tx, field, value)
    db.commit()
    db.refresh(tx)
    return _tx_out(tx)


@router.delete("/{transaction_id}", status_code=204)
def delete_transaction(transaction_id: str, db: DbDep, user: CurrentUserDep) -> None:
    household_id = _household_id(user)
    tx = _get_transaction(db, household_id, user.id, transaction_id)
    if tx.type == "transfer":
        if tx.transfer_group_id is None:
            raise HTTPException(status_code=409, detail="La transferencia está incompleta")
        rows = _transfer_rows(db, tx.transfer_group_id)
        _assert_transfer_access(rows, household_id, user.id, db)
        group = db.get(TransferGroup, tx.transfer_group_id)
        db.delete(rows[0])
        db.delete(rows[1])
        if group is not None:
            db.delete(group)
        db.commit()
        return
    db.delete(tx)
    db.commit()
