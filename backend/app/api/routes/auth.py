import io
import warnings
from datetime import datetime, timezone
from typing import Annotated

import jwt
from fastapi import APIRouter, Body, Depends, File, HTTPException, Request, Response, UploadFile
from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy import func, select

from app.api.deps import CurrentUserDep, DbDep
from app.core.security import (
    create_access_token,
    decode_token_claims,
    hash_password,
    revoke_user_refresh_tokens,
    verify_password,
)
from app.core.rate_limit import client_ip, limiter
from app.config import settings
from app.models import Account, Category, Household, Invitation, RefreshToken, User, new_id
from app.schemas.auth import (
    ChangePasswordRequest,
    JoinRequest,
    LoginRequest,
    OnboardingRequest,
    ProfileUpdateRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.seed import DEFAULT_CATEGORIES
from app.services import storage

router = APIRouter(prefix="/auth", tags=["auth"])

_MAX_AVATAR_PIXELS = 16_000_000
_MAX_AVATAR_DIMENSION = 8_192


def _now() -> datetime:
    """'Ahora' en UTC como datetime naive (las columnas son DateTime naive)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _set_session_cookie(response: Response, token: str) -> None:
    """Guarda el JWT en una cookie httpOnly (issue #34).

    El token vive 15 min y el refresh window 30 días; la cookie expira con el
    refresh window para que el navegador no retenga credenciales muertas.
    ``SameSite=lax`` bloquea el envío en cross-site (CSRF) y ``httpOnly`` lo
    pone fuera del alcance de ``document.cookie`` (XSS no lo exfiltra).
    """
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        max_age=settings.refresh_token_expiry_days * 24 * 3600,
        expires=None,
        httponly=settings.session_cookie_httponly,
        secure=settings.session_cookie_secure,
        samesite=settings.session_cookie_samesite,
        path="/",
    )


def _clear_session_cookie(response: Response) -> None:
    """Borra la cookie de sesión en logout/cambio de password."""
    response.delete_cookie(
        key=settings.session_cookie_name,
        httponly=settings.session_cookie_httponly,
        secure=settings.session_cookie_secure,
        samesite=settings.session_cookie_samesite,
        path="/",
    )


def _get_user_by_email(db: DbDep, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email))


def _limit_register(request: Request) -> None:
    limiter.check(
        f"register:{client_ip(request)}",
        settings.auth_register_limit,
        settings.auth_register_window_seconds,
    )


def _limit_login(request: Request) -> None:
    limiter.check(
        f"login:{client_ip(request)}",
        settings.auth_login_limit,
        settings.auth_login_window_seconds,
    )


def _limit_join(request: Request) -> None:
    limiter.check(
        f"join:{client_ip(request)}",
        settings.auth_join_limit,
        settings.auth_join_window_seconds,
    )


@router.post("/register", status_code=201, response_model=TokenResponse)
def register(
    db: DbDep,
    body: Annotated[RegisterRequest, Body()],
    response: Response,
    _: Annotated[None, Depends(_limit_register)],
):
    if _get_user_by_email(db, body.email) is not None:
        raise HTTPException(status_code=409, detail="El correo ya está registrado")

    user = User(
        email=body.email,
        hashed_password=hash_password(body.password),
        name=body.name,
    )
    db.add(user)
    db.flush()

    household = Household(
        name=body.household_name, currency_code="MXN", owner_id=user.id
    )
    db.add(household)
    db.flush()
    household.owner_id = user.id
    user.household_id = household.id

    for cat in DEFAULT_CATEGORIES:
        db.add(Category(household_id=household.id, active=True, **cat))

    # Cuenta inicial para que el hogar no arranque vacío
    db.add(Account(household_id=household.id, name="Efectivo", kind="cash"))
    token, jti = create_access_token(db, user.id)
    db.commit()
    _set_session_cookie(response, token)

    return TokenResponse(access_token=token, token_identifier=jti)


@router.post("/login", response_model=TokenResponse)
def login(
    db: DbDep,
    body: Annotated[LoginRequest, Body()],
    response: Response,
    _: Annotated[None, Depends(_limit_login)],
):
    user = _get_user_by_email(db, body.email)
    if user is None or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")
    token, jti = create_access_token(db, user.id)
    db.commit()
    _set_session_cookie(response, token)
    return TokenResponse(access_token=token, token_identifier=jti)


def _user_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        household_id=user.household_id,
        sex=user.sex,
        birth_date=user.birth_date,
        has_avatar=user.avatar_path is not None,
        avatar_updated_at=user.avatar_updated_at,
        onboarding_completed=user.onboarding_completed_at is not None,
    )


@router.get("/me", response_model=UserResponse)
def me(current_user: CurrentUserDep):
    return _user_response(current_user)


@router.patch("/me", response_model=UserResponse)
def update_profile(
    db: DbDep,
    current_user: CurrentUserDep,
    body: Annotated[ProfileUpdateRequest, Body()],
):
    if "name" in body.model_fields_set:
        current_user.name = body.name
    if "sex" in body.model_fields_set:
        current_user.sex = body.sex
    if "birth_date" in body.model_fields_set:
        current_user.birth_date = body.birth_date
    db.commit()
    return _user_response(current_user)


@router.post("/logout", status_code=204)
def logout(
    db: DbDep,
    request: Request,
    current_user: CurrentUserDep,
) -> Response:
    """Borra la cookie httpOnly de sesión del dispositivo (issue #34).

    El SPA no puede eliminarla (httpOnly). Además revoca el jti del token
    vigente (el que autenticó la petición, por cookie o Bearer) para que ni el
    refresh ni el token en vuelo sigan sirviendo tras cerrar sesión.
    """
    token = request.cookies.get(settings.session_cookie_name)
    auth_header = request.headers.get("Authorization", "")
    if token is None and auth_header.startswith("Bearer "):
        token = auth_header[7:]
    if token:
        try:
            payload = decode_token_claims(token, verify_exp=False)
            revoke_user_refresh_tokens(db, payload["sub"])
        except jwt.PyJWTError:
            pass  # token caducado/revocado: nada que revocar
    response = Response(status_code=204)
    _clear_session_cookie(response)
    return response


@router.post("/change-password", status_code=204)
def change_password(
    db: DbDep,
    current_user: CurrentUserDep,
    body: Annotated[ChangePasswordRequest, Body()],
    response: Response,
) -> Response:
    if not verify_password(body.current_password, current_user.hashed_password):
        raise HTTPException(status_code=401, detail="La contraseña actual es incorrecta")
    current_user.hashed_password = hash_password(body.new_password)
    # A password change voids every outstanding session (including this
    # device: it must log in again). Legacy tokens without a jti cannot be
    # revoked and simply live out their JWT exp.
    revoke_user_refresh_tokens(db, current_user.id)
    db.commit()
    response.status_code = 204
    _clear_session_cookie(response)
    return response


@router.post("/refresh", response_model=TokenResponse)
def refresh(
    db: DbDep,
    request: Request,
    response: Response,
    _: Annotated[None, Depends(_limit_login)],
    body: Annotated[RefreshRequest, Body()] = RefreshRequest(),
):
    """Renames an expired-but-not-revoked access token.

    The presented token is decoded with ``verify_exp=False``: it may be past
    its 15-minute life (that is the point), but it must be unrevoked and
    inside the 30-day refresh window. On success the old token is rotated
    (revoked) and a fresh one returned; replaying the old token then fails,
    so a stolen token is a single-use credential once renewed.

    El token se toma del body si lo hay; si no, de la cookie httpOnly
    (issue #34): el SPA no puede leer el JWT para reenviarlo.
    """
    token = body.access_token or request.cookies.get(settings.session_cookie_name)
    if not token:
        raise HTTPException(status_code=401, detail="Token inválido")
    try:
        payload = decode_token_claims(token, verify_exp=False)
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Token inválido") from None
    jti = payload.get("jti")
    if jti is None:
        # Legacy tokens cannot be renewed: they predate the revocation table.
        raise HTTPException(status_code=401, detail="Token inválido")
    row = db.scalar(select(RefreshToken).where(RefreshToken.jti == jti).with_for_update())
    now = _now()
    if row is None or row.revoked_at is not None or row.expires_at <= now:
        raise HTTPException(status_code=401, detail="Token revocado o caducado")
    user = db.get(User, payload["sub"])
    if user is None:
        raise HTTPException(status_code=401, detail="Token inválido")
    row.revoked_at = now  # rotation: the presented token is now a spent credential
    token, jti = create_access_token(db, user.id)
    db.commit()
    _set_session_cookie(response, token)
    return TokenResponse(access_token=token, token_identifier=jti)


def _avatar_key(user: User) -> str:
    return f"avatars/{user.id}/{new_id()}.webp"


@router.post("/me/avatar", response_model=UserResponse)
async def upload_avatar(
    db: DbDep,
    current_user: CurrentUserDep,
    file: Annotated[UploadFile, File(...)],
):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=415, detail="El archivo debe ser una imagen")
    max_source_size = 2 * 1024 * 1024
    source = await file.read(max_source_size + 1)
    if len(source) > max_source_size:
        raise HTTPException(status_code=413, detail="La imagen no puede superar 2 MiB")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(source)) as image:
                width, height = image.size
                # Reject oversized compressed images before Pillow decodes pixels.
                if (
                    width > _MAX_AVATAR_DIMENSION
                    or height > _MAX_AVATAR_DIMENSION
                    or width * height > _MAX_AVATAR_PIXELS
                ):
                    raise ValueError("La imagen excede el límite de dimensiones")
                image.load()
                avatar = ImageOps.fit(
                    image.convert("RGB"),
                    (512, 512),
                    method=Image.Resampling.LANCZOS,
                    centering=(0.5, 0.5),
                )
        encoded = io.BytesIO()
        avatar.save(encoded, format="WEBP")
    except (
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
        OSError,
        UnidentifiedImageError,
        ValueError,
    ):
        raise HTTPException(status_code=422, detail="La imagen no es válida") from None

    locked_user = db.scalar(
        select(User).where(User.id == current_user.id).with_for_update()
    )
    if locked_user is None:
        raise HTTPException(status_code=401, detail="No autenticado o token inválido")
    user_id = locked_user.id
    previous_path = locked_user.avatar_path
    object_key = _avatar_key(locked_user)
    try:
        storage.put_avatar(object_key, encoded.getvalue())
    except storage.StorageError:
        raise HTTPException(status_code=502, detail="No se pudo guardar el avatar") from None
    locked_user.avatar_path = object_key
    locked_user.avatar_updated_at = _now()
    try:
        db.commit()
    except Exception:
        persisted_path: str | None = None
        state_known = False
        try:
            # rollback clears the failed transaction before checking whether the
            # commit actually made this immutable key the persisted pointer.
            db.rollback()
            persisted_path = db.scalar(
                select(User.avatar_path).where(User.id == user_id)
            )
            state_known = True
        except Exception:
            # When persistence state is unknown, retain an inaccessible object
            # rather than risk deleting a successfully committed avatar.
            pass
        if state_known and persisted_path != object_key:
            try:
                storage.delete_avatar(object_key)
            except storage.StorageError:
                pass
        raise HTTPException(status_code=500, detail="No se pudo actualizar el avatar") from None
    if previous_path is not None and previous_path != object_key:
        try:
            storage.delete_avatar(previous_path)
        except storage.StorageError:
            pass
    return _user_response(locked_user)


@router.get("/me/avatar")
def get_avatar(current_user: CurrentUserDep) -> Response:
    if current_user.avatar_path is None:
        raise HTTPException(status_code=404, detail="Avatar no encontrado")
    try:
        content = storage.get_avatar(current_user.avatar_path)
    except storage.StorageNotFoundError:
        raise HTTPException(status_code=404, detail="Avatar no encontrado") from None
    except storage.StorageError:
        raise HTTPException(status_code=502, detail="No se pudo leer el avatar") from None
    return Response(
        content=content,
        media_type="image/webp",
        headers={"Cache-Control": "private, no-store"},
    )


@router.delete("/me/avatar", status_code=204)
def delete_avatar(db: DbDep, current_user: CurrentUserDep) -> Response:
    locked_user = db.scalar(
        select(User).where(User.id == current_user.id).with_for_update()
    )
    if locked_user is None:
        raise HTTPException(status_code=401, detail="No autenticado o token inválido")
    if locked_user.avatar_path is None:
        raise HTTPException(status_code=404, detail="Avatar no encontrado")
    avatar_path = locked_user.avatar_path
    locked_user.avatar_path = None
    locked_user.avatar_updated_at = None
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="No se pudo borrar el avatar") from None
    try:
        storage.delete_avatar(avatar_path)
    except storage.StorageError:
        pass
    return Response(status_code=204)


@router.patch("/me/onboarding", response_model=UserResponse)
def set_onboarding(
    db: DbDep,
    current_user: CurrentUserDep,
    body: Annotated[OnboardingRequest, Body()],
):
    """Marca el wizard inicial como completado (o lo reabre con `completed:
    false`). Idempotente: repetir la llamada no mueve la fecha ya guardada."""
    if body.completed:
        if current_user.onboarding_completed_at is None:
            current_user.onboarding_completed_at = _now()
    else:
        current_user.onboarding_completed_at = None
    db.commit()
    return _user_response(current_user)


@router.post("/join", status_code=201, response_model=TokenResponse)
def join(
    db: DbDep,
    body: Annotated[JoinRequest, Body()],
    response: Response,
    _: Annotated[None, Depends(_limit_join)],
):
    invitation = db.scalar(
        select(Invitation).where(Invitation.token == body.token).with_for_update()
    )
    if invitation is None:
        raise HTTPException(status_code=404, detail="Invitación no encontrada")
    now = _now()
    if invitation.used_at is not None or invitation.expires_at <= now:
        raise HTTPException(status_code=410, detail="Invitación inválida o expirada")
    # Locking the household serializes joins with invitation creation and other
    # joins, so the member count remains valid under concurrent requests.
    household = db.scalar(
        select(Household)
        .where(Household.id == invitation.household_id)
        .with_for_update()
    )
    if household is None:
        raise HTTPException(status_code=404, detail="Hogar no encontrado")
    member_count = db.scalar(
        select(func.count(User.id)).where(User.household_id == household.id)
    )
    if member_count >= settings.max_members_per_household:
        raise HTTPException(status_code=409, detail="Este hogar alcanzó el máximo de miembros")
    if _get_user_by_email(db, body.email) is not None:
        raise HTTPException(status_code=409, detail="El correo ya está registrado")

    user = User(
        email=body.email,
        hashed_password=hash_password(body.password),
        name=body.name,
        household_id=invitation.household_id,
        # El hogar ya está configurado por quien invitó: sin wizard.
        onboarding_completed_at=now,
    )
    db.add(user)
    db.flush()  # user.id (default) is needed by create_access_token
    invitation.used_at = now
    token, jti = create_access_token(db, user.id)
    db.commit()
    _set_session_cookie(response, token)

    return TokenResponse(access_token=token, token_identifier=jti)
