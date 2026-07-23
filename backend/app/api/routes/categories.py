from fastapi import APIRouter, HTTPException
from sqlalchemy import func, select

from app.api.deps import CurrentUserDep, DbDep
from app.models import Category, Transaction, User
from app.schemas.categories import CategoryCreate, CategoryOut, CategoryUpdate

router = APIRouter(prefix="/categories", tags=["categories"])


def _household_id(user: User) -> str:
    if user.household_id is None:
        raise HTTPException(status_code=400, detail="El usuario no pertenece a un hogar")
    return user.household_id


def _get_category(db, household_id: str, category_id: str) -> Category:
    category = db.get(Category, category_id)
    if category is None or category.household_id != household_id:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    return category


@router.get("")
def list_categories(db: DbDep, user: CurrentUserDep) -> list[CategoryOut]:
    household_id = _household_id(user)
    categories = db.scalars(
        select(Category)
        .where(Category.household_id == household_id)
        .order_by(Category.name, Category.id)
    ).all()
    return [
        CategoryOut(
            id=c.id,
            household_id=c.household_id,
            name=c.name,
            icon=c.icon,
            color=c.color,
            type=c.type,
            active=c.active,
        )
        for c in categories
    ]


@router.post("", status_code=201)
def create_category(
    payload: CategoryCreate, db: DbDep, user: CurrentUserDep
) -> CategoryOut:
    household_id = _household_id(user)
    category = Category(
        household_id=household_id,
        name=payload.name,
        icon=payload.icon,
        color=payload.color,
        type=payload.type,
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return CategoryOut(
        id=category.id,
        household_id=category.household_id,
        name=category.name,
        icon=category.icon,
        color=category.color,
        type=category.type,
        active=category.active,
    )


@router.patch("/{category_id}")
def update_category(
    category_id: str, payload: CategoryUpdate, db: DbDep, user: CurrentUserDep
) -> CategoryOut:
    household_id = _household_id(user)
    category = _get_category(db, household_id, category_id)
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(category, field, value)
    db.commit()
    db.refresh(category)
    return CategoryOut(
        id=category.id,
        household_id=category.household_id,
        name=category.name,
        icon=category.icon,
        color=category.color,
        type=category.type,
        active=category.active,
    )


@router.delete("/{category_id}", status_code=204)
def delete_category(category_id: str, db: DbDep, user: CurrentUserDep) -> None:
    household_id = _household_id(user)
    category = _get_category(db, household_id, category_id)
    has_movements = db.scalar(
        select(func.count())
        .select_from(Transaction)
        .where(Transaction.category_id == category.id)
    )
    if has_movements:
        raise HTTPException(status_code=409, detail="La categoría tiene movimientos")
    db.delete(category)
    db.commit()
