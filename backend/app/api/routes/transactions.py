from datetime import date
from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import delete, or_, select
from sqlalchemy.exc import IntegrityError

from app.api.deps import CurrentUserDep, DbDep
from app.models import (
    Account,
    Category,
    RecurringRule,
    Transaction,
    TransactionEditEvent,
    TransactionSplit,
    TransferGroup,
    User,
)
from app.schemas.transactions import (
    TransactionCreate,
    TransactionOut,
    TransactionSplitInput,
    TransactionSplitOut,
    TransactionUpdate,
)
from app.services.recurring import advance, materialize_due
from app.services.account_access import can_operate, visible_accounts
from app.services.instalment_plans import active_plan_for
from app.services.reconciliation import invalidate_completed_reconciliation

router = APIRouter(prefix="/transactions", tags=["transactions"])

_MONTH_PATTERN = r"^\d{4}-\d{2}$"


def _household_id(user: User) -> str:
    if user.household_id is None:
        raise HTTPException(status_code=400, detail="El usuario no pertenece a un hogar")
    return user.household_id


def _get_transaction(
    db, household_id: str, user_id: str, transaction_id: str, *, for_update: bool = False
) -> Transaction:
    stmt = select(Transaction).join(Account).where(
        Transaction.id == transaction_id,
        Transaction.household_id == household_id,
        Transaction.deleted_at.is_(None),
        visible_accounts(user_id),
    )
    if for_update:
        stmt = stmt.with_for_update(of=Transaction)
    tx = db.scalar(stmt)
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
                Transaction.deleted_at.is_(None),
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
        reconciliation_status=tx.reconciliation_status,
        is_split=tx.is_split,
        splits=[TransactionSplitOut(category_id=split.category_id, amount=float(split.amount)) for split in tx.splits],
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
        or tx.is_split != bool(payload.splits)
    ):
        return False
    if tx.is_split and not _same_splits(tx.splits, payload.splits):
        return False
    if payload.repeat is None:
        return tx.recurring_rule_id is None
    rule = db.get(RecurringRule, tx.recurring_rule_id)
    return rule is not None and rule.frequency == payload.repeat


def _money(value: Decimal | float) -> Decimal:
    """Compare amounts at the database's fixed four-decimal money scale."""
    return Decimal(str(value)).quantize(Decimal("0.0001"))


def _same_splits(rows: list[TransactionSplit], splits: list[TransactionSplitInput]) -> bool:
    return sorted((row.category_id, _money(row.amount)) for row in rows) == sorted(
        (split.category_id, _money(split.amount)) for split in splits
    )


def _split_snapshot(tx: Transaction) -> list[dict[str, object]]:
    return [
        {"category_id": split.category_id, "amount": float(split.amount)}
        for split in sorted(tx.splits, key=lambda row: row.category_id)
    ]


def _validate_splits(
    db, household_id: str, user_id: str, tx_type: str, amount: Decimal | float,
    splits: list[TransactionSplitInput],
) -> None:
    if len(splits) < 2:
        raise HTTPException(status_code=422, detail="Un movimiento dividido requiere al menos dos categorías")
    if len({split.category_id for split in splits}) != len(splits):
        raise HTTPException(status_code=422, detail="Una categoría no se puede repetir en un movimiento dividido")
    if sum((_money(split.amount) for split in splits), Decimal()) != _money(amount):
        raise HTTPException(status_code=422, detail="Las asignaciones deben sumar exactamente el monto")
    for split in splits:
        category = db.get(Category, split.category_id)
        if (
            category is None or category.household_id != household_id or category.deleted
            or not category.active or category.type != tx_type
        ):
            raise HTTPException(status_code=422, detail="La categoría de una asignación no es válida")


def _snapshot(tx: Transaction, fields: tuple[str, ...]) -> dict[str, object]:
    snapshot: dict[str, object] = {}
    for field in fields:
        value = getattr(tx, field)
        if isinstance(value, Decimal):
            value = float(value)
        elif isinstance(value, date):
            value = value.isoformat()
        snapshot[field] = value
    return snapshot


def _assert_replay_access(tx: Transaction, household_id: str, user_id: str, db) -> None:
    if tx.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Transacción no encontrada")
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


def _transfer_rows(db, group_id: str, *, for_update: bool = False) -> list[Transaction]:
    stmt = select(Transaction).where(
        Transaction.transfer_group_id == group_id,
        Transaction.deleted_at.is_(None),
    )
    if for_update:
        stmt = stmt.with_for_update()
    rows = db.scalars(stmt).all()
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
    stmt = select(Transaction).join(Account).where(
        Transaction.household_id == household_id,
        Transaction.deleted_at.is_(None),
        visible_accounts(user.id),
    )
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
        stmt = stmt.where(or_(
            Transaction.category_id == category_id,
            Transaction.splits.any(TransactionSplit.category_id == category_id),
        ))
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
                Transaction.deleted_at.is_(None),
            ))
            if existing_transaction is not None:
                _assert_replay_access(existing_transaction, household_id, user.id, db)
                raise HTTPException(status_code=409, detail="El clientId ya se usó con un movimiento distinto")
            reverted_transaction = db.scalar(select(Transaction.id).where(
                Transaction.household_id == household_id,
                Transaction.client_id == client_id,
                Transaction.deleted_at.is_not(None),
            ).limit(1))
            if reverted_transaction is not None:
                raise HTTPException(
                    status_code=409,
                    detail="El clientId ya se usó con una transacción revertida",
                )
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
                Transaction.deleted_at.is_(None),
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
    assert payload.account_id is not None
    if payload.splits:
        _validate_splits(db, household_id, user.id, payload.type, payload.amount, payload.splits)
    else:
        assert payload.category_id is not None
        _validate_refs(db, household_id, user.id, payload.category_id, payload.account_id)
    tx = Transaction(
        household_id=household_id,
        client_id=client_id,
        type=payload.type,
        amount=payload.amount,
        category_id=None if payload.splits else payload.category_id,
        is_split=bool(payload.splits),
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
            if payload.splits:
                db.add_all([
                    TransactionSplit(transaction_id=tx.id, category_id=split.category_id, amount=split.amount)
                    for split in payload.splits
                ])
    except IntegrityError:
        if client_id is None:
            raise
        existing = db.scalar(
            select(Transaction).where(
                Transaction.household_id == household_id,
                Transaction.client_id == client_id,
                Transaction.deleted_at.is_(None),
            )
        )
        if existing is None:
            # The unique key may belong to a reverted row, which must never be
            # returned as a successful offline replay.
            raise HTTPException(
                status_code=409,
                detail="El clientId ya se usó con una transacción revertida",
            ) from None
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
    # PATCH and import revert share this row lock. If revert wins while PATCH is
    # waiting, the deleted_at predicate below makes PATCH return 404 instead of
    # changing a reverted transaction.
    tx = _get_transaction(db, household_id, user.id, transaction_id, for_update=True)
    if tx.type == "transfer":
        if tx.transfer_group_id is None:
            raise HTTPException(status_code=409, detail="La transferencia está incompleta")
        rows = _transfer_rows(db, tx.transfer_group_id, for_update=True)
        _assert_transfer_access(rows, household_id, user.id, db)
        data = payload.model_dump(exclude_unset=True)
        if "splits" in data:
            raise HTTPException(status_code=422, detail="Las transferencias no se pueden dividir")
        source = next(row for row in rows if row.transfer_direction == "outflow")
        destination = next(row for row in rows if row.transfer_direction == "inflow")
        source_id = data.pop("source_account_id", source.account_id)
        destination_id = data.pop("destination_account_id", destination.account_id)
        if "account_id" in data:
            raise HTTPException(status_code=422, detail="Usa cuenta origen y destino para editar una transferencia")
        if "category_id" in data or data.get("type") not in (None, "transfer"):
            raise HTTPException(status_code=422, detail="Una transferencia no usa categoría ni tipo de movimiento")
        _validate_transfer_accounts(db, household_id, user.id, source_id, destination_id)
        before_snapshots: dict[str, dict[str, object]] = {}
        for row in rows:
            before_snapshots[row.id] = _snapshot(row, ("amount", "date", "note", "account_id"))
            row.amount = data.get("amount", row.amount)
            row.date = data.get("date", row.date)
            row.note = data.get("note", row.note)
        source.account_id = source_id
        destination.account_id = destination_id
        for row in rows:
            before = before_snapshots[row.id]
            after = _snapshot(row, ("amount", "date", "note", "account_id"))
            if row.import_batch_id is not None and before != after:
                db.add(TransactionEditEvent(
                    transaction_id=row.id, edited_by_id=user.id,
                    before_snapshot=before, after_snapshot=after,
                ))
            if before != after:
                invalidate_completed_reconciliation(db, row)
        db.commit()
        db.refresh(tx)
        return _tx_out(tx, db, user.id)
    data = payload.model_dump(exclude_unset=True)
    if ("amount" in data or "account_id" in data) and active_plan_for(db, tx.id) is not None:
        raise HTTPException(
            status_code=409,
            detail="No se puede editar el monto o la cuenta de una compra con un plan de instalados activo",
        )
    if data.get("type") == "transfer" or "source_account_id" in data or "destination_account_id" in data:
        raise HTTPException(status_code=422, detail="Una transacción existente no se puede convertir en transferencia")
    splits = data.pop("splits", None)
    if splits is not None:
        splits = [TransactionSplitInput.model_validate(split) for split in splits]
    if splits is not None and data.get("type") == "transfer":
        raise HTTPException(status_code=422, detail="Una transacción existente no se puede convertir en transferencia")
    category_id = data.get("category_id", tx.category_id)
    account_id = data.get("account_id", tx.account_id)
    if splits is not None:
        if splits:
            _validate_splits(
                db, household_id, user.id, data.get("type", tx.type),
                data.get("amount", tx.amount), splits,
            )
            data["category_id"] = None
            data["is_split"] = True
        else:
            if not category_id:
                raise HTTPException(status_code=422, detail="El movimiento requiere categoría y cuenta")
            data["is_split"] = False
    elif tx.is_split and "amount" in data:
        raise HTTPException(status_code=422, detail="Actualiza las asignaciones al cambiar el monto")
    if ("category_id" in data or "account_id" in data) and not data.get("is_split", tx.is_split):
        _validate_refs(db, household_id, user.id, category_id, account_id)
    before = _snapshot(tx, tuple(data))
    if splits is not None:
        before["splits"] = _split_snapshot(tx)
    for field, value in data.items():
        setattr(tx, field, value)
    if splits is not None:
        # Flush removals before replacements: the same category may remain in
        # the new allocation set and is protected by a parent/category unique key.
        db.execute(delete(TransactionSplit).where(TransactionSplit.transaction_id == tx.id))
        db.flush()
        db.expire(tx, ["splits"])
        if splits:
            tx.splits.extend(
                TransactionSplit(category_id=split.category_id, amount=split.amount) for split in splits
            )
        db.flush()
    after = _snapshot(tx, tuple(data))
    if splits is not None:
        after["splits"] = _split_snapshot(tx)
    if tx.import_batch_id is not None and before != after:
        db.add(TransactionEditEvent(
            transaction_id=tx.id, edited_by_id=user.id,
            before_snapshot=before, after_snapshot=after,
        ))
    if before != after:
        invalidate_completed_reconciliation(db, tx)
    db.commit()
    db.refresh(tx)
    return _tx_out(tx)


@router.delete("/{transaction_id}", status_code=204)
def delete_transaction(transaction_id: str, db: DbDep, user: CurrentUserDep) -> None:
    household_id = _household_id(user)
    tx = _get_transaction(db, household_id, user.id, transaction_id)
    if tx.import_batch_id is not None:
        raise HTTPException(status_code=409, detail="No se puede eliminar una transacción importada")
    if active_plan_for(db, tx.id) is not None:
        raise HTTPException(status_code=409, detail="La compra tiene un plan de instalados activo; cancela el plan primero")
    if tx.type == "transfer":
        if tx.transfer_group_id is None:
            raise HTTPException(status_code=409, detail="La transferencia está incompleta")
        rows = _transfer_rows(db, tx.transfer_group_id)
        _assert_transfer_access(rows, household_id, user.id, db)
        group = db.get(TransferGroup, tx.transfer_group_id)
        for row in rows:
            invalidate_completed_reconciliation(db, row)
        db.delete(rows[0])
        db.delete(rows[1])
        # The group is the FK parent; remove both transfer rows first.
        db.flush()
        if group is not None:
            db.delete(group)
        db.commit()
        return
    invalidate_completed_reconciliation(db, tx)
    db.delete(tx)
    db.commit()
