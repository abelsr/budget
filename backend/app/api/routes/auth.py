from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Body, HTTPException
from sqlalchemy import select

from app.api.deps import CurrentUserDep, DbDep
from app.core.security import create_access_token, hash_password, verify_password
from app.models import Category, Household, Invitation, User
from app.schemas.auth import (
    JoinRequest,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.seed import DEFAULT_CATEGORIES

router = APIRouter(prefix="/auth", tags=["auth"])


def _now() -> datetime:
    """'Ahora' en UTC como datetime naive (las columnas son DateTime naive)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _get_user_by_email(db: DbDep, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email))


@router.post("/register", status_code=201, response_model=TokenResponse)
def register(db: DbDep, body: Annotated[RegisterRequest, Body()]):
    if _get_user_by_email(db, body.email) is not None:
        raise HTTPException(status_code=409, detail="El correo ya está registrado")

    household = Household(name=body.household_name, currency_code="MXN")
    db.add(household)
    db.flush()

    for cat in DEFAULT_CATEGORIES:
        db.add(Category(household_id=household.id, active=True, **cat))

    user = User(
        email=body.email,
        hashed_password=hash_password(body.password),
        name=body.name,
        household_id=household.id,
    )
    db.add(user)
    db.commit()

    return TokenResponse(access_token=create_access_token(user.id))


@router.post("/login", response_model=TokenResponse)
def login(db: DbDep, body: Annotated[LoginRequest, Body()]):
    user = _get_user_by_email(db, body.email)
    if user is None or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")
    return TokenResponse(access_token=create_access_token(user.id))


@router.get("/me", response_model=UserResponse)
def me(current_user: CurrentUserDep):
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        household_id=current_user.household_id,
    )


@router.post("/join", status_code=201, response_model=TokenResponse)
def join(db: DbDep, body: Annotated[JoinRequest, Body()]):
    invitation = db.scalar(
        select(Invitation).where(Invitation.token == body.token)
    )
    if invitation is None:
        raise HTTPException(status_code=404, detail="Invitación no encontrada")
    now = _now()
    if invitation.used_at is not None or invitation.expires_at < now:
        raise HTTPException(status_code=410, detail="Invitación inválida o expirada")
    if _get_user_by_email(db, body.email) is not None:
        raise HTTPException(status_code=409, detail="El correo ya está registrado")

    user = User(
        email=body.email,
        hashed_password=hash_password(body.password),
        name=body.name,
        household_id=invitation.household_id,
    )
    db.add(user)
    invitation.used_at = now
    db.commit()

    return TokenResponse(access_token=create_access_token(user.id))
