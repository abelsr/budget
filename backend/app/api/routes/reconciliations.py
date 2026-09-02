from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, HTTPException, Response
from sqlalchemy import select

from app.api.deps import CurrentUserDep, DbDep
from app.models import Account, ReconciliationSession, Transaction, User
from app.schemas.reconciliations import (
    ReconciliationCreate,
    ReconciliationSessionDetail,
    ReconciliationSessionOut,
    ReconciliationToggle,
    ReconciliationTransactionOut,
)
from app.services.account_access import can_operate

router = APIRouter(tags=["reconciliations"])


def _household_id(user: User) -> str:
    if user.household_id is None:
        raise HTTPException(status_code=400, detail="El usuario no pertenece a un hogar")
    return user.household_id


def _account(db, household_id: str, user_id: str, account_id: str, *, for_update: bool = False) -> Account:
    stmt = select(Account).where(Account.id == account_id)
    if for_update:
        stmt = stmt.with_for_update()
    account = db.scalar(stmt)
    if account is None or account.household_id != household_id or not can_operate(account, user_id):
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")
    return account


def _session(db, account_id: str, session_id: str) -> ReconciliationSession:
    session = db.scalar(select(ReconciliationSession).where(
        ReconciliationSession.id == session_id,
        ReconciliationSession.account_id == account_id,
    ))
    if session is None:
        raise HTTPException(status_code=404, detail="Conciliación no encontrada")
    return session


def _effect(transaction: Transaction) -> Decimal:
    amount = Decimal(str(transaction.amount))
    return amount if transaction.type == "income" or transaction.transfer_direction == "inflow" else -amount


def _session_out(session: ReconciliationSession) -> ReconciliationSessionOut:
    return ReconciliationSessionOut(
        id=session.id, account_id=session.account_id, statement_date=session.statement_date,
        statement_balance=float(session.statement_balance), status=session.status,
        completed_at=session.completed_at, created_at=session.created_at,
    )


def _detail(db, account: Account, session: ReconciliationSession) -> ReconciliationSessionDetail:
    transactions = db.scalars(select(Transaction).where(
        Transaction.account_id == account.id,
        Transaction.deleted_at.is_(None),
        Transaction.date <= session.statement_date,
    ).order_by(Transaction.date.desc(), Transaction.created_at.desc())).all()
    reconciled_effect = sum((_effect(tx) for tx in transactions if tx.reconciliation_status == "reconciled"), Decimal("0"))
    pending_effect = sum((_effect(tx) for tx in transactions if tx.reconciliation_status == "pending"), Decimal("0"))
    reconciled_balance = Decimal(str(account.opening_balance)) + reconciled_effect
    difference = Decimal(str(session.statement_balance)) - reconciled_balance
    base = _session_out(session).model_dump()
    return ReconciliationSessionDetail(
        **base,
        pending_total=float(pending_effect),
        reconciled_total=float(reconciled_effect),
        reconciled_balance=float(reconciled_balance),
        difference=float(difference),
        transactions=[ReconciliationTransactionOut(
            id=tx.id, type=tx.type, amount=float(tx.amount), date=tx.date, note=tx.note,
            reconciliation_status=tx.reconciliation_status,
        ) for tx in transactions],
    )


@router.post("/accounts/{account_id}/reconciliations", status_code=201)
def create_reconciliation(
    account_id: str, payload: ReconciliationCreate, response: Response, db: DbDep, user: CurrentUserDep,
) -> ReconciliationSessionOut:
    household_id = _household_id(user)
    # The account row serializes concurrent attempts to start a reconciliation.
    _account(db, household_id, user.id, account_id, for_update=True)
    existing = db.scalar(select(ReconciliationSession).where(
        ReconciliationSession.account_id == account_id,
        ReconciliationSession.status == "open",
    ).limit(1))
    if existing is not None:
        # Returning the draft lets the ledger resume a reconciliation after a
        # sheet was closed or the page was reloaded, without creating a second one.
        response.status_code = 200
        return _session_out(existing)
    session = ReconciliationSession(
        account_id=account_id, household_id=household_id, statement_date=payload.statement_date,
        statement_balance=payload.statement_balance, created_by_id=user.id,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return _session_out(session)


@router.get("/accounts/{account_id}/reconciliations/{session_id}")
def get_reconciliation(
    account_id: str, session_id: str, db: DbDep, user: CurrentUserDep,
) -> ReconciliationSessionDetail:
    account = _account(db, _household_id(user), user.id, account_id)
    return _detail(db, account, _session(db, account_id, session_id))


@router.post("/transactions/{transaction_id}/reconciliation")
def toggle_reconciliation(
    transaction_id: str, payload: ReconciliationToggle, db: DbDep, user: CurrentUserDep,
) -> ReconciliationTransactionOut:
    household_id = _household_id(user)
    transaction = db.scalar(select(Transaction).join(Account).where(
        Transaction.id == transaction_id, Transaction.household_id == household_id,
        Transaction.deleted_at.is_(None),
    ).with_for_update())
    if transaction is None:
        raise HTTPException(status_code=404, detail="Transacción no encontrada")
    _account(db, household_id, user.id, transaction.account_id)
    active = db.scalar(select(ReconciliationSession).where(
        ReconciliationSession.account_id == transaction.account_id,
        ReconciliationSession.status == "open",
    ).with_for_update())
    if active is None:
        raise HTTPException(status_code=409, detail="La cuenta no tiene una conciliación abierta")
    if transaction.date > active.statement_date:
        raise HTTPException(status_code=422, detail="La transacción es posterior a la fecha de estado de cuenta")
    if transaction.reconciliation_session_id not in (None, active.id):
        raise HTTPException(status_code=409, detail="La transacción pertenece a una conciliación cerrada")
    transaction.reconciliation_status = "reconciled" if payload.reconciled else "pending"
    transaction.reconciliation_session_id = active.id if payload.reconciled else None
    db.commit()
    return ReconciliationTransactionOut(
        id=transaction.id, type=transaction.type, amount=float(transaction.amount),
        date=transaction.date, note=transaction.note,
        reconciliation_status=transaction.reconciliation_status,
    )


@router.post("/accounts/{account_id}/reconciliations/{session_id}/complete")
def complete_reconciliation(
    account_id: str, session_id: str, db: DbDep, user: CurrentUserDep,
) -> ReconciliationSessionOut:
    account = _account(db, _household_id(user), user.id, account_id)
    session = _session(db, account_id, session_id)
    if session.status != "open":
        raise HTTPException(status_code=409, detail="La conciliación ya no está abierta")
    detail = _detail(db, account, session)
    if Decimal(str(detail.difference)).quantize(Decimal("0.0001")) != Decimal("0.0000"):
        raise HTTPException(status_code=409, detail="La diferencia debe ser cero para completar la conciliación")
    session.status = "completed"
    session.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()
    db.refresh(session)
    return _session_out(session)
