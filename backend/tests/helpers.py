"""Helpers de tests compartidos (issue #48).

JWT/headers y creación de usuarios por sesión, antes duplicados en 8+
módulos de test. Los tests que ya importaban helpers de otro módulo
(test_core) ahora importan de aquí; no debe haber acoplamiento entre
módulos de test.
"""

from datetime import datetime, timedelta, timezone

import jwt
from sqlalchemy.orm import Session

from app.config import settings
from app.core.security import hash_password
from app.models import User


def make_token(user: User) -> str:
    """JWT de test: sub = user.id, exp = ahora + 1h (con settings de app)."""
    return jwt.encode(
        {"sub": user.id, "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


def auth_headers(user: User) -> dict[str, str]:
    """Headers de autorización Bearer para el usuario dado."""
    return {"Authorization": f"Bearer {make_token(user)}"}


def create_user(session: Session, email: str, name: str, **kw) -> User:
    """Crea un usuario persistido (flush) en la sesión de test.

    Acepta overrides de modelo (p. ej. ``household_id=...``).
    """
    user = User(email=email, hashed_password=hash_password("password123"), name=name, **kw)
    session.add(user)
    session.flush()
    return user


# ---------- Creación de recursos vía HTTP (antes en test_core.py) ----------


def create_category(client, headers, **overrides):
    payload = {"name": "Comida", "icon": "utensils", "color": "#30b0c7", "type": "expense"}
    payload.update(overrides)
    resp = client.post("/categories", json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


def create_account(client, headers, **overrides):
    payload = {"name": "Efectivo", "kind": "cash", "openingBalance": 100.0}
    payload.update(overrides)
    resp = client.post("/accounts", json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


def create_transaction(client, headers, category_id, account_id, **overrides):
    payload = {
        "type": "expense",
        "amount": 10.0,
        "categoryId": category_id,
        "accountId": account_id,
        "date": "2026-07-10",
    }
    payload.update(overrides)
    resp = client.post("/transactions", json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


# ---------- CSV de importación (antes en test_imports.py) ----------


def _csv_upload(client, url, headers, account_id, content, **fields):
    data = {"accountId": account_id, **fields}
    return client.post(
        url,
        data=data,
        files={"file": ("statement.csv", content, "text/csv")},
        headers=headers,
    )


def _mapping() -> str:
    return '{"date":"Fecha","amount":"Importe","description":"Concepto"}'
