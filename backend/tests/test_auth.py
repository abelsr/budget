import io
from datetime import date, datetime, timedelta, timezone

from PIL import Image
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Account, Category, Household, Invitation, User
from app.api.routes import auth
from app.config import settings
from app.services import storage


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
    assert user.email_verified is False
    assert user.household_id is not None
    household = session.get(Household, user.household_id)
    assert household is not None
    assert household.owner_id == user.id

    count = session.scalar(
        select(func.count(Category.id)).where(
            Category.household_id == user.household_id
        )
    )
    assert count == 10

    # Cuenta inicial "Efectivo" para que el hogar no arranque vacío
    account = session.scalar(
        select(Account).where(Account.household_id == user.household_id)
    )
    assert account is not None
    assert account.kind == "cash"


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


def test_auth_rate_limits_return_429(client, monkeypatch):
    monkeypatch.setattr(settings, "auth_register_limit", 1)
    monkeypatch.setattr(settings, "auth_login_limit", 1)
    monkeypatch.setattr(settings, "auth_join_limit", 1)

    assert _register(client).status_code == 201
    response = _register(client, "another@example.com")
    assert response.status_code == 429
    assert response.headers["retry-after"]

    assert client.post(
        "/auth/login", json={"email": "ana@example.com", "password": "password123"}
    ).status_code == 200
    assert client.post(
        "/auth/login", json={"email": "ana@example.com", "password": "password123"}
    ).status_code == 429

    assert client.post("/auth/join", json={
        "token": "missing", "email": "join@example.com", "password": "password123", "name": "Join"
    }).status_code == 404
    assert client.post("/auth/join", json={
        "token": "missing", "email": "other@example.com", "password": "password123", "name": "Other"
    }).status_code == 429


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


def test_join_flow(client, session: Session, monkeypatch):
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

    locked_queries = []
    original_scalar = session.scalar

    def capture_scalar(statement, *args, **kwargs):
        if getattr(statement, "_for_update_arg", None) is not None:
            locked_queries.append(statement)
        return original_scalar(statement, *args, **kwargs)

    monkeypatch.setattr(session, "scalar", capture_scalar)

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
    # SQLite no aplica bloqueos de fila; esta aserción conserva la intención de
    # serialización que se ejecuta como FOR UPDATE en PostgreSQL.
    assert locked_queries

    user = session.scalar(select(User).where(User.email == "bob@example.com"))
    assert user.household_id == me["householdId"]
    # Quien entra por invitación no pasa por el wizard: el hogar ya está listo
    assert user.onboarding_completed_at is not None

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


def test_join_rejects_invitation_at_exact_expiry(client, session: Session, monkeypatch):
    token = _register(client).json()["accessToken"]
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).json()
    expires_at = _now()
    session.add(
        Invitation(
            household_id=me["householdId"],
            token="expires-now",
            created_by_id=me["id"],
            expires_at=expires_at,
        )
    )
    session.commit()
    monkeypatch.setattr(auth, "_now", lambda: expires_at)

    response = client.post(
        "/auth/join",
        json={
            "token": "expires-now",
            "email": "bob@example.com",
            "password": "password123",
            "name": "Bob",
        },
    )

    assert response.status_code == 410
    assert response.json()["detail"] == "Invitación inválida o expirada"


def test_join_rejects_when_household_member_limit_is_reached(client, session, monkeypatch):
    token = _register(client).json()["accessToken"]
    owner = client.get("/auth/me", headers=_headers(token)).json()
    monkeypatch.setattr(settings, "max_members_per_household", 1)
    session.add(Invitation(
        household_id=owner["householdId"],
        token="member-limit",
        created_by_id=owner["id"],
        expires_at=_now() + timedelta(days=1),
    ))
    session.commit()

    response = client.post("/auth/join", json={
        "token": "member-limit", "email": "bob@example.com", "password": "password123", "name": "Bob"
    })
    assert response.status_code == 409
    assert response.json()["detail"] == "Este hogar alcanzó el máximo de miembros"
    assert session.scalar(select(User).where(User.email == "bob@example.com")) is None


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_register_leaves_onboarding_pending(client):
    token = _register(client).json()["accessToken"]
    resp = client.get("/auth/me", headers=_headers(token))
    assert resp.json()["onboardingCompleted"] is False


def test_complete_onboarding_is_idempotent(client, session: Session):
    token = _register(client).json()["accessToken"]

    resp = client.patch(
        "/auth/me/onboarding", json={"completed": True}, headers=_headers(token)
    )
    assert resp.status_code == 200
    assert resp.json()["onboardingCompleted"] is True

    user = session.scalar(select(User).where(User.email == "ana@example.com"))
    first = user.onboarding_completed_at
    assert first is not None

    # Repetir no mueve la fecha ya guardada
    resp = client.patch(
        "/auth/me/onboarding", json={"completed": True}, headers=_headers(token)
    )
    assert resp.status_code == 200
    session.refresh(user)
    assert user.onboarding_completed_at == first

    # El flag persiste entre peticiones (recargar no repite el wizard)
    resp = client.get("/auth/me", headers=_headers(token))
    assert resp.json()["onboardingCompleted"] is True


def test_reopen_onboarding(client):
    token = _register(client).json()["accessToken"]
    client.patch("/auth/me/onboarding", json={"completed": True}, headers=_headers(token))

    resp = client.patch(
        "/auth/me/onboarding", json={"completed": False}, headers=_headers(token)
    )
    assert resp.status_code == 200
    assert resp.json()["onboardingCompleted"] is False


def test_onboarding_requires_token(client):
    assert client.patch("/auth/me/onboarding", json={"completed": True}).status_code == 401


def test_profile_update_and_optional_fields_can_be_cleared(client):
    token = _register(client).json()["accessToken"]

    resp = client.patch(
        "/auth/me",
        json={"name": "Ana Maria", "sex": "female", "birthDate": "1990-05-20"},
        headers=_headers(token),
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Ana Maria"
    assert resp.json()["sex"] == "female"
    assert resp.json()["birthDate"] == "1990-05-20"
    assert resp.json()["hasAvatar"] is False
    assert resp.json()["avatarUpdatedAt"] is None

    resp = client.patch(
        "/auth/me",
        json={"sex": None, "birthDate": None},
        headers=_headers(token),
    )
    assert resp.status_code == 200
    assert resp.json()["sex"] is None
    assert resp.json()["birthDate"] is None


def test_profile_update_rejects_empty_and_invalid_values(client):
    token = _register(client).json()["accessToken"]

    assert client.patch("/auth/me", json={}, headers=_headers(token)).status_code == 422
    assert (
        client.patch("/auth/me", json={"name": ""}, headers=_headers(token)).status_code
        == 422
    )
    assert (
        client.patch("/auth/me", json={"sex": "other"}, headers=_headers(token)).status_code
        == 422
    )
    assert (
        client.patch(
            "/auth/me", json={"birthDate": str(date.today() + timedelta(days=1))}, headers=_headers(token)
        ).status_code
        == 422
    )
    assert (
        client.patch("/auth/me", json={"birthDate": "1900-01-01"}, headers=_headers(token)).status_code
        == 422
    )


def test_change_password_requires_current_password_and_keeps_token_valid(client):
    token = _register(client).json()["accessToken"]
    wrong_current = "incorrecta"
    current = "password123"
    too_short = "corta"
    replacement = "nueva123"

    resp = client.post(
        "/auth/change-password",
        json={"currentPassword": wrong_current, "newPassword": replacement},
        headers=_headers(token),
    )
    assert resp.status_code == 401
    assert resp.json()["detail"] == "La contraseña actual es incorrecta"
    assert (
        client.post(
            "/auth/change-password",
            json={"currentPassword": current, "newPassword": too_short},
            headers=_headers(token),
        ).status_code
        == 422
    )

    resp = client.post(
        "/auth/change-password",
        json={"currentPassword": current, "newPassword": replacement},
        headers=_headers(token),
    )
    assert resp.status_code == 204
    assert client.get("/auth/me", headers=_headers(token)).status_code == 200
    assert (
        client.post(
            "/auth/login", json={"email": "ana@example.com", "password": "password123"}
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/auth/login", json={"email": "ana@example.com", "password": "nueva123"}
        ).status_code
        == 200
    )


def _avatar_file() -> bytes:
    image = Image.new("RGB", (800, 400), "blue")
    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def test_avatar_lifecycle_uses_webp_storage(client, monkeypatch):
    objects: dict[str, bytes] = {}

    def put_avatar(key: str, content: bytes) -> None:
        objects[key] = content

    def get_avatar(key: str) -> bytes:
        if key not in objects:
            raise storage.StorageNotFoundError("no existe")
        return objects[key]

    def delete_avatar(key: str) -> None:
        del objects[key]

    monkeypatch.setattr(storage, "put_avatar", put_avatar)
    monkeypatch.setattr(storage, "get_avatar", get_avatar)
    monkeypatch.setattr(storage, "delete_avatar", delete_avatar)
    token = _register(client).json()["accessToken"]

    assert client.get("/auth/me/avatar", headers=_headers(token)).status_code == 404
    resp = client.post(
        "/auth/me/avatar",
        files={"file": ("avatar.png", _avatar_file(), "image/png")},
        headers=_headers(token),
    )
    assert resp.status_code == 200
    assert resp.json()["hasAvatar"] is True
    assert resp.json()["avatarUpdatedAt"] is not None
    first_key, first_content = next(iter(objects.items()))
    with Image.open(io.BytesIO(first_content)) as image:
        assert image.format == "WEBP"
        assert image.size == (512, 512)

    resp = client.post(
        "/auth/me/avatar",
        files={"file": ("avatar.png", _avatar_file(), "image/png")},
        headers=_headers(token),
    )
    assert resp.status_code == 200
    assert first_key not in objects
    assert len(objects) == 1
    second_key, content = next(iter(objects.items()))
    assert second_key != first_key

    resp = client.get("/auth/me/avatar", headers=_headers(token))
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/webp"
    assert resp.headers["cache-control"] == "private, no-store"
    assert resp.content == content

    assert client.delete("/auth/me/avatar", headers=_headers(token)).status_code == 204
    assert objects == {}
    assert client.get("/auth/me", headers=_headers(token)).json()["hasAvatar"] is False


def test_avatar_upload_errors_do_not_update_profile(client, monkeypatch):
    token = _register(client).json()["accessToken"]

    assert (
        client.post(
            "/auth/me/avatar",
            files={"file": ("archivo.txt", b"texto", "text/plain")},
            headers=_headers(token),
        ).status_code
        == 415
    )
    assert (
        client.post(
            "/auth/me/avatar",
            files={"file": ("rota.png", b"no es una imagen", "image/png")},
            headers=_headers(token),
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/auth/me/avatar",
            files={"file": ("grande.png", b"x" * (2 * 1024 * 1024 + 1), "image/png")},
            headers=_headers(token),
        ).status_code
        == 413
    )

    def fail_put(key: str, content: bytes) -> None:
        raise storage.StorageError("S3 caído")

    monkeypatch.setattr(storage, "put_avatar", fail_put)
    assert (
        client.post(
            "/auth/me/avatar",
            files={"file": ("avatar.png", _avatar_file(), "image/png")},
            headers=_headers(token),
        ).status_code
        == 502
    )
    assert client.get("/auth/me", headers=_headers(token)).json()["hasAvatar"] is False

    objects: dict[str, bytes] = {}

    def put_avatar(key: str, content: bytes) -> None:
        objects[key] = content

    monkeypatch.setattr(storage, "put_avatar", put_avatar)
    assert (
        client.post(
            "/auth/me/avatar",
            files={"file": ("avatar.png", _avatar_file(), "image/png")},
            headers=_headers(token),
        ).status_code
        == 200
    )

    def fail_get(key: str) -> bytes:
        raise storage.StorageError("S3 caído")

    def fail_delete(key: str) -> None:
        raise storage.StorageError("S3 caído")

    monkeypatch.setattr(storage, "get_avatar", fail_get)
    monkeypatch.setattr(storage, "delete_avatar", fail_delete)
    assert client.get("/auth/me/avatar", headers=_headers(token)).status_code == 502
    # Cleanup is best effort after the profile pointer has been cleared.
    assert client.delete("/auth/me/avatar", headers=_headers(token)).status_code == 204
    assert client.get("/auth/me", headers=_headers(token)).json()["hasAvatar"] is False


def test_avatar_rejects_oversized_dimensions_before_decode(client, monkeypatch):
    token = _register(client).json()["accessToken"]

    class DeceptiveImage:
        size = (100_000, 100_000)
        load_called = False

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def load(self):
            self.load_called = True

    image = DeceptiveImage()
    monkeypatch.setattr(auth.Image, "open", lambda source: image)

    resp = client.post(
        "/auth/me/avatar",
        files={"file": ("avatar.png", _avatar_file(), "image/png")},
        headers=_headers(token),
    )
    assert resp.status_code == 422
    assert image.load_called is False


def test_avatar_upload_removes_unpersisted_new_key_after_commit_failure(client, session: Session, monkeypatch):
    objects: dict[str, bytes] = {}
    puts: list[tuple[str, bytes]] = []
    deletes: list[str] = []

    def put_avatar(key: str, content: bytes) -> None:
        puts.append((key, content))
        objects[key] = content

    def get_avatar(key: str) -> bytes:
        if key not in objects:
            raise storage.StorageNotFoundError("no existe")
        return objects[key]

    def delete_avatar(key: str) -> None:
        deletes.append(key)
        objects.pop(key, None)

    monkeypatch.setattr(storage, "put_avatar", put_avatar)
    monkeypatch.setattr(storage, "get_avatar", get_avatar)
    monkeypatch.setattr(storage, "delete_avatar", delete_avatar)
    token = _register(client).json()["accessToken"]
    assert (
        client.post(
            "/auth/me/avatar",
            files={"file": ("avatar.png", _avatar_file(), "image/png")},
            headers=_headers(token),
        ).status_code
        == 200
    )
    avatar_key, original = next(iter(objects.items()))
    replacement = Image.new("RGB", (400, 800), "red")
    replacement_bytes = io.BytesIO()
    replacement.save(replacement_bytes, format="PNG")

    real_commit = session.commit

    def fail_commit() -> None:
        raise RuntimeError("base de datos caída")

    monkeypatch.setattr(session, "commit", fail_commit)
    resp = client.post(
        "/auth/me/avatar",
        files={"file": ("replacement.png", replacement_bytes.getvalue(), "image/png")},
        headers=_headers(token),
    )
    assert resp.status_code == 500
    assert objects[avatar_key] == original
    failed_key = puts[-1][0]
    assert failed_key != avatar_key
    assert failed_key in deletes
    # Failed uploads only remove their own new key; no old bytes are rewritten.
    assert [key for key, content in puts if content == original] == [avatar_key]

    monkeypatch.setattr(session, "commit", real_commit)
    assert client.get("/auth/me", headers=_headers(token)).json()["hasAvatar"] is True


def test_new_avatar_is_removed_after_commit_failure(client, session: Session, monkeypatch):
    objects: dict[str, bytes] = {}

    def put_avatar(key: str, content: bytes) -> None:
        objects[key] = content

    monkeypatch.setattr(storage, "put_avatar", put_avatar)
    monkeypatch.setattr(storage, "delete_avatar", lambda key: objects.pop(key, None))
    token = _register(client).json()["accessToken"]

    def fail_commit() -> None:
        raise RuntimeError("base de datos caída")

    real_commit = session.commit
    monkeypatch.setattr(session, "commit", fail_commit)
    resp = client.post(
        "/auth/me/avatar",
        files={"file": ("avatar.png", _avatar_file(), "image/png")},
        headers=_headers(token),
    )
    assert resp.status_code == 500
    assert objects == {}

    monkeypatch.setattr(session, "commit", real_commit)
    assert client.get("/auth/me", headers=_headers(token)).json()["hasAvatar"] is False


def test_avatar_upload_keeps_new_key_when_commit_outcome_persisted(client, session: Session, monkeypatch):
    objects: dict[str, bytes] = {}

    def put_avatar(key: str, content: bytes) -> None:
        objects[key] = content

    monkeypatch.setattr(storage, "put_avatar", put_avatar)
    monkeypatch.setattr(storage, "delete_avatar", lambda key: objects.pop(key, None))
    token = _register(client).json()["accessToken"]
    assert (
        client.post(
            "/auth/me/avatar",
            files={"file": ("avatar.png", _avatar_file(), "image/png")},
            headers=_headers(token),
        ).status_code
        == 200
    )
    old_key = next(iter(objects))
    real_commit = session.commit

    def commit_then_fail() -> None:
        real_commit()
        raise RuntimeError("resultado incierto")

    monkeypatch.setattr(session, "commit", commit_then_fail)
    assert (
        client.post(
            "/auth/me/avatar",
            files={"file": ("avatar.png", _avatar_file(), "image/png")},
            headers=_headers(token),
        ).status_code
        == 500
    )
    new_key = next(reversed(objects))
    assert new_key != old_key
    assert new_key in objects

    monkeypatch.setattr(session, "commit", real_commit)
    assert client.get("/auth/me", headers=_headers(token)).json()["hasAvatar"] is True


def test_avatar_delete_keeps_object_after_commit_failure(client, session: Session, monkeypatch):
    objects: dict[str, bytes] = {}
    deletes: list[str] = []

    def put_avatar(key: str, content: bytes) -> None:
        objects[key] = content

    def get_avatar(key: str) -> bytes:
        return objects[key]

    def delete_avatar(key: str) -> None:
        deletes.append(key)
        del objects[key]

    monkeypatch.setattr(storage, "put_avatar", put_avatar)
    monkeypatch.setattr(storage, "get_avatar", get_avatar)
    monkeypatch.setattr(storage, "delete_avatar", delete_avatar)
    token = _register(client).json()["accessToken"]
    assert (
        client.post(
            "/auth/me/avatar",
            files={"file": ("avatar.png", _avatar_file(), "image/png")},
            headers=_headers(token),
        ).status_code
        == 200
    )
    avatar_key, original = next(iter(objects.items()))

    real_commit = session.commit
    monkeypatch.setattr(session, "commit", lambda: (_ for _ in ()).throw(RuntimeError()))
    assert client.delete("/auth/me/avatar", headers=_headers(token)).status_code == 500
    assert objects[avatar_key] == original
    assert deletes == []

    monkeypatch.setattr(session, "commit", real_commit)
    assert client.get("/auth/me", headers=_headers(token)).json()["hasAvatar"] is True


def test_avatar_requires_authentication(client):
    assert client.post("/auth/me/avatar", files={"file": ("a.png", b"x", "image/png")}).status_code == 401
    assert client.get("/auth/me/avatar").status_code == 401
    assert client.delete("/auth/me/avatar").status_code == 401
