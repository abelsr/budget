from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Category, Invitation, User


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _register(client, email="ana@example.com"):
    return client.post(
        "/auth/register",
        json={
            "email": email,
            "password": "password123",
            "name": "Ana",
            "householdName": "Casa Ana",
        },
    )


def test_register_creates_user_household_token_and_categories(client, session: Session):
    resp = _register(client)
    assert resp.status_code == 201
    data = resp.json()
    assert data["accessToken"]
    assert data["tokenType"] == "bearer"

    user = session.scalar(select(User).where(User.email == "ana@example.com"))
    assert user is not None
    assert user.household_id is not None

    count = session.scalar(
        select(func.count(Category.id)).where(
            Category.household_id == user.household_id
        )
    )
    assert count == 10


def test_register_duplicate_email_returns_409(client):
    assert _register(client).status_code == 201
    resp = _register(client)
    assert resp.status_code == 409
    assert resp.json()["detail"] == "El correo ya está registrado"


def test_login_success_and_wrong_password(client):
    _register(client)

    resp = client.post(
        "/auth/login",
        json={"email": "ana@example.com", "password": "password123"},
    )
    assert resp.status_code == 200
    assert resp.json()["accessToken"]

    resp = client.post(
        "/auth/login",
        json={"email": "ana@example.com", "password": "wrongpassword"},
    )
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Credenciales incorrectas"


def test_me_requires_token_and_returns_user(client):
    resp = client.get("/auth/me")
    assert resp.status_code == 401

    token = _register(client).json()["accessToken"]
    resp = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "ana@example.com"
    assert data["name"] == "Ana"
    assert data["householdId"]


def test_join_flow(client, session: Session):
    token = _register(client).json()["accessToken"]
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).json()

    invitation = Invitation(
        household_id=me["householdId"],
        token="tok123",
        created_by_id=me["id"],
        expires_at=_now() + timedelta(days=1),
    )
    session.add(invitation)
    session.commit()

    resp = client.post(
        "/auth/join",
        json={
            "token": "tok123",
            "email": "bob@example.com",
            "password": "password123",
            "name": "Bob",
        },
    )
    assert resp.status_code == 201
    assert resp.json()["accessToken"]

    user = session.scalar(select(User).where(User.email == "bob@example.com"))
    assert user.household_id == me["householdId"]

    # Reintentar con el mismo token → 410 (ya usada)
    resp = client.post(
        "/auth/join",
        json={
            "token": "tok123",
            "email": "carol@example.com",
            "password": "password123",
            "name": "Carol",
        },
    )
    assert resp.status_code == 410
    assert resp.json()["detail"] == "Invitación inválida o expirada"

    # Token inexistente → 404
    resp = client.post(
        "/auth/join",
        json={
            "token": "noexiste",
            "email": "dan@example.com",
            "password": "password123",
            "name": "Dan",
        },
    )
    assert resp.status_code == 404
