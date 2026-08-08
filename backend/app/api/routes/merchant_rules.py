from fastapi import APIRouter, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.deps import CurrentUserDep, DbDep
from app.models import Category, MerchantRule, User
from app.schemas.merchant_rules import MerchantRuleCreate, MerchantRuleOut
from app.services.categorization import normalize_match_text

router = APIRouter(prefix="/merchant-rules", tags=["merchant rules"])


def _household_id(user: User) -> str:
    if user.household_id is None:
        raise HTTPException(status_code=400, detail="El usuario no pertenece a un hogar")
    return user.household_id


def _out(rule: MerchantRule) -> MerchantRuleOut:
    return MerchantRuleOut(
        id=rule.id, household_id=rule.household_id, pattern=rule.pattern,
        category_id=rule.category_id, category_name=rule.category.name,
        category_type=rule.category.type,
    )


@router.get("")
def list_merchant_rules(db: DbDep, user: CurrentUserDep) -> list[MerchantRuleOut]:
    rules = db.scalars(
        select(MerchantRule).join(Category).where(
            MerchantRule.household_id == _household_id(user), Category.deleted.is_(False)
        ).order_by(MerchantRule.pattern, MerchantRule.id)
    ).all()
    return [_out(rule) for rule in rules]


@router.post("", status_code=201)
def create_merchant_rule(
    payload: MerchantRuleCreate, db: DbDep, user: CurrentUserDep
) -> MerchantRuleOut:
    household_id = _household_id(user)
    match_text = normalize_match_text(payload.pattern)
    if not match_text:
        raise HTTPException(status_code=422, detail="El comercio debe contener letras o números")
    category = db.get(Category, payload.category_id)
    if category is None or category.household_id != household_id or category.deleted or not category.active:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    rule = MerchantRule(
        household_id=household_id, pattern=payload.pattern.strip(), match_text=match_text,
        category_id=category.id,
    )
    db.add(rule)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Ya existe una regla para este comercio") from None
    db.refresh(rule)
    return _out(rule)


@router.delete("/{rule_id}", status_code=204)
def delete_merchant_rule(rule_id: str, db: DbDep, user: CurrentUserDep) -> None:
    rule = db.scalar(select(MerchantRule).where(
        MerchantRule.id == rule_id, MerchantRule.household_id == _household_id(user)
    ))
    if rule is None:
        raise HTTPException(status_code=404, detail="Regla no encontrada")
    db.delete(rule)
    db.commit()
