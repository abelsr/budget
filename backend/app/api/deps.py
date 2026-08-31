from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import get_current_user as _verify
from app.database import get_db
from app.models import User

DbDep = Annotated[Session, Depends(get_db)]

_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    db: DbDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User:
    """Valida el JWT Bearer y regresa el usuario.

    Contrato del token emitido por la app: ``{"sub", "exp", "jti"}`` firmado
    con ``settings.jwt_secret/algorithm``; el ``jti`` debe corresponder a una
    fila ``refresh_tokens`` no revocada. Tokens sin ``jti`` (pre-deploy /
    fixtures) se aceptan solo sobre el JWT, hasta su ``exp``.
    """
    unauthorized = HTTPException(
        status_code=401,
        detail="No autenticado o token inválido",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized
    user = _verify(db, credentials.credentials)
    if user is None:
        raise unauthorized
    return user


CurrentUserDep = Annotated[User, Depends(get_current_user)]
