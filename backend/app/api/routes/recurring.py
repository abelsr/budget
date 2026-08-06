from datetime import date, timedelta

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.api.deps import CurrentUserDep, DbDep
from app.models import Account, Category, RecurringRule, Transaction, TransactionEditEvent, User
from app.schemas.recurring import (
    RecurringRuleCreate,
    RecurringRuleOut,
    RecurringRuleUpdate,
)
from app.services.recurring import MAX_BACKFILL_DAYS, materialize_due, next_future_run
from app.services.account_access import can_operate, visible_accounts

router = APIRouter(prefix="/recurring-rules", tags=["recurring"])


def _household_id(user: User) -> str:
    if user.household_id is None:
        raise HTTPException(status_code=400, detail="El usuario no pertenece a un hogar")
    return user.household_id


def _get_rule(db, household_id: str, user_id: str, rule_id: str) -> RecurringRule:
    rule = db.scalar(select(RecurringRule).join(Account).where(
        RecurringRule.id == rule_id,
        RecurringRule.household_id == household_id,
        visible_accounts(user_id),
    ))
    if rule is None:
        raise HTTPException(status_code=404, detail="Regla no encontrada")
    return rule


def _validate_refs(db, household_id: str, user_id: str, category_id: str, account_id: str) -> None:
    category = db.get(Category, category_id)
    if category is None or category.household_id != household_id or category.deleted:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    account = db.get(Account, account_id)
    if account is None or account.household_id != household_id or not can_operate(account, user_id):
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")


def _validate_next_run_date(next_run_date: date) -> None:
    if next_run_date < date.today() - timedelta(days=MAX_BACKFILL_DAYS):
        raise HTTPException(
            status_code=422,
            detail="La próxima fecha no puede estar a más de un año en el pasado",
        )


def _rule_out(rule: RecurringRule) -> RecurringRuleOut:
    return RecurringRuleOut(
        id=rule.id,
        household_id=rule.household_id,
        type=rule.type,
        amount=float(rule.amount),
        category_id=rule.category_id,
        account_id=rule.account_id,
        created_by_id=rule.created_by_id,
        frequency=rule.frequency,
        next_run_date=rule.next_run_date,
        note=rule.note,
        active=rule.active,
    )


@router.get("")
def list_rules(db: DbDep, user: CurrentUserDep) -> list[RecurringRuleOut]:
    household_id = _household_id(user)
    # Materializa antes de listar: si no, la pantalla mostraría "próxima" en
    # una fecha que ya pasó, que es justo lo que el usuario viene a revisar.
    materialize_due(db, household_id, user.id)
    rules = db.scalars(
        select(RecurringRule)
        .join(Account)
        .where(RecurringRule.household_id == household_id, visible_accounts(user.id))
        .order_by(RecurringRule.next_run_date, RecurringRule.id)
    ).all()
    return [_rule_out(rule) for rule in rules]


@router.post("", status_code=201)
def create_rule(
    payload: RecurringRuleCreate, db: DbDep, user: CurrentUserDep
) -> RecurringRuleOut:
    household_id = _household_id(user)
    _validate_refs(db, household_id, user.id, payload.category_id, payload.account_id)
    _validate_next_run_date(payload.next_run_date)
    rule = RecurringRule(
        household_id=household_id,
        type=payload.type,
        amount=payload.amount,
        category_id=payload.category_id,
        account_id=payload.account_id,
        created_by_id=user.id,
        frequency=payload.frequency,
        next_run_date=payload.next_run_date,
        anchor_day=(
            payload.next_run_date.day if payload.frequency == "monthly" else None
        ),
        note=payload.note,
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return _rule_out(rule)


@router.patch("/{rule_id}")
def update_rule(
    rule_id: str, payload: RecurringRuleUpdate, db: DbDep, user: CurrentUserDep
) -> RecurringRuleOut:
    household_id = _household_id(user)
    rule = _get_rule(db, household_id, user.id, rule_id)
    data = payload.model_dump(exclude_unset=True)
    reactivating = data.get("active") is True and not rule.active
    if reactivating:
        category = db.get(Category, rule.category_id)
        if category is None or category.deleted:
            raise HTTPException(
                status_code=409,
                detail="La categoría de la regla fue eliminada",
            )
    for field, value in data.items():
        setattr(rule, field, value)
    # Reanudar salta lo que estuvo pausado: quien apagó la regla en marzo no
    # quiere que al prenderla en julio le caigan cuatro meses de renta.
    if reactivating:
        rule.next_run_date = next_future_run(rule, date.today())
    db.commit()
    db.refresh(rule)
    return _rule_out(rule)


@router.delete("/{rule_id}", status_code=204)
def delete_rule(rule_id: str, db: DbDep, user: CurrentUserDep) -> None:
    household_id = _household_id(user)
    rule = _get_rule(db, household_id, user.id, rule_id)
    # A reverted transaction retains its historical rule reference. The FK is
    # restrictive, so deleting its rule would either corrupt that history or
    # leave an invalid reference.
    if db.scalar(select(Transaction.id).where(
        Transaction.recurring_rule_id == rule.id,
        Transaction.deleted_at.is_not(None),
    ).limit(1)) is not None:
        raise HTTPException(status_code=409, detail="La regla tiene movimientos revertidos")
    transactions = db.scalars(select(Transaction).where(
        Transaction.recurring_rule_id == rule.id,
        Transaction.deleted_at.is_(None),
    )).all()
    for transaction in transactions:
        if transaction.import_batch_id is not None:
            db.add(TransactionEditEvent(
                transaction_id=transaction.id,
                edited_by_id=user.id,
                before_snapshot={"recurring_rule_id": rule.id},
                after_snapshot={"recurring_rule_id": None},
            ))
        transaction.recurring_rule_id = None
    # Flush child references before deleting the restrictive FK parent.
    db.flush()
    db.delete(rule)
    db.commit()
