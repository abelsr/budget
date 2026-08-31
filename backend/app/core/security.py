import uuid
from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash
from sqlalchemy import update
from sqlalchemy.orm import Session

from app.config import settings
from app.models import RefreshToken, User

password_hash = PasswordHash.recommended()


def _utcnow() -> datetime:
    """'Ahora' en UTC naive (las columnas DateTime del repo son naive)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return password_hash.verify(plain, hashed)


def create_access_token(db: Session, user_id: str) -> str:
    """Signs a short-lived access token and records its revocation row.

    Payload: ``{"sub": user_id, "exp": now + jwt_expire_minutes, "jti": <uuid>}``.
    The ``jti`` keys the ``refresh_tokens`` row that lets ``/auth/refresh``
    renew the token within the refresh window and lets
    ``revoke_user_refresh_tokens`` void it on password change / removal.
    """
    jti = uuid.uuid4().hex
    now = _utcnow()
    db.add(
        RefreshToken(
            jti=jti,
            user_id=user_id,
            issued_at=now,
            expires_at=now + timedelta(days=settings.refresh_token_expiry_days),
        )
    )
    db.flush()
    return jwt.encode(
        {
            "sub": user_id,
            "exp": now + timedelta(minutes=settings.jwt_expire_minutes),
            "jti": jti,
        },
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


def decode_token_claims(token: str, *, verify_exp: bool = True) -> dict:
    """Decodes and verifies signature + required claims; returns the payload.

    Raises ``jwt.PyJWTError`` on any failure. ``verify_exp=False`` is used by
    ``/auth/refresh`` to accept an already-expired (but not revoked) token.
    """
    return jwt.decode(
        token,
        settings.jwt_secret,
        algorithms=[settings.jwt_algorithm],
        options={"require": ["exp", "sub"], "verify_exp": verify_exp},
    )


def validate_token_row(db: Session, jti: str | None, *, allow_expired: bool) -> None:
    """Raises ``ValueError`` unless the token's refresh row is still usable.

    - ``jti is None`` → legacy token (pre-deploy 30-day tokens, fixtures):
      nothing to check against; the JWT's own ``exp`` is the only gate.
    - revoked or past the refresh window → ``ValueError``.
    """
    if jti is None:
        return
    row = db.get(RefreshToken, jti)
    if row is None or row.revoked_at is not None:
        raise ValueError("token revocado")
    if not allow_expired and row.expires_at <= _utcnow():
        raise ValueError("token revocado")


def revoke_user_refresh_tokens(db: Session, user_id: str) -> int:
    """Revokes every outstanding token of a user (password change / removal).

    Returns the number of rows revoked. Already-revoked rows are untouched.
    """
    result = db.execute(
        update(RefreshToken)
        .where(
            RefreshToken.user_id == user_id,
            RefreshToken.revoked_at.is_(None),
        )
        .values(revoked_at=_utcnow())
    )
    db.flush()
    return result.rowcount or 0


def get_current_user(db: Session, token: str) -> User | None:
    """Validates a Bearer token and returns the user, or ``None`` if invalid.

    Contract: tokens signed by this app carry ``jti`` and must have a
    non-revoked, unexpired refresh row. Tokens without ``jti`` are legacy
    (issued before the revocation table existed, or test fixtures) and are
    accepted on the JWT alone until they expire.
    """
    try:
        payload = decode_token_claims(token)
    except jwt.PyJWTError:
        return None
    user_id = payload.get("sub")
    if not user_id:
        return None
    try:
        validate_token_row(db, payload.get("jti"), allow_expired=False)
    except ValueError:
        return None
    user = db.get(User, user_id)
    if user is None:
        return None
    return user
