from typing import Annotated

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.config import settings
from app.core.security import get_current_user as _verify
from app.database import get_db
from app.models import User

DbDep = Annotated[Session, Depends(get_db)]

_bearer = HTTPBearer(auto_error=False)


def _resolve_token(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> str | None:
    """Token por header Bearer (preferente) o por cookie httpOnly (issue #34).

    El cookie lleva el mismo JWT; se consulta cuando no hay header para que
    la SPA no tenga que leerlo (está en una cookie no accesible a JS).
    """
    if credentials is not None:
        return credentials.credentials
    cookie_token = request.cookies.get(settings.session_cookie_name)
    if cookie_token:
        return cookie_token
    return None


def get_current_user(
    db: DbDep,
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User:
    """Valida el JWT (header Bearer o cookie httpOnly) y regresa el usuario.

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
    token = _resolve_token(request, credentials)
    if token is None:
        raise unauthorized
    user = _verify(db, token)
    if user is None:
        raise unauthorized
    return user


CurrentUserDep = Annotated[User, Depends(get_current_user)]
