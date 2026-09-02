"""Tests de la revocación de tokens (issue #36).

Tokens emitidos por la app llevan ``jti`` + fila en ``refresh_tokens``; el
endpooint ``/auth/refresh`` renueva un token caducado (no revocado) rotándolo,
y ``change_password`` / ``remove_member`` revocan todas las sesiones del
usuario. freezegun ancla los casos de expiración.
"""

from datetime import datetime, timedelta, timezone

import jwt
import pytest
from freezegun import freeze_time

from app.config import settings
from app.models import RefreshToken, User

FROZEN = "2026-08-15 12:00:00"


def _now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _register(client, email="ana@example.com", password="password123", name="Ana"):
    resp = client.post(
        "/auth/register",
        json={
            "email": email,
            "password": password,
            "name": name,
            "householdName": "Hogar " + name,
        },
    )
    assert resp.status_code == 201
    return resp.json()


def _forge_token(user_id: str, *, with_jti=None, minutes=15):
    """Forges a token the way the app signs it (or without jti when testing legacy)."""
    now = _now_naive()
    payload = {"sub": user_id, "exp": now + timedelta(minutes=minutes)}
    if with_jti is not None:
        payload["jti"] = with_jti
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_issued_token_has_jti_and_refresh_row(client, session):
    data = _register(client)
    token = data["accessToken"]
    payload = jwt.decode(
        token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
    )
    assert "jti" in payload and payload["sub"]
    row = session.get(RefreshToken, payload["jti"])
    assert row is not None
    assert row.user_id == payload["sub"]
    assert row.revoked_at is None
    # Refresh window ~30 days out.
    assert row.expires_at > _now_naive() + timedelta(days=29)


def test_expired_token_is_rejected(client):
    with freeze_time(FROZEN, tz_offset=0):
        data = _register(client)
        token = data["accessToken"]
    # 16 minutes later: past the 15-minute access-life.
    later = "2026-08-15 12:16:00"
    with freeze_time(later, tz_offset=0):
        assert client.get("/auth/me", headers=_headers(token)).status_code == 401


def test_change_password_revokes_presenting_session(client):
    data = _register(client)
    token = data["accessToken"]
    assert client.get("/auth/me", headers=_headers(token)).status_code == 200
    resp = client.post(
        "/auth/change-password",
        json={"currentPassword": "password123", "newPassword": "nueva12345"},
        headers=_headers(token),
    )
    assert resp.status_code == 204
    # The old (app-issued, jti-backed) token is now revoked.
    assert client.get("/auth/me", headers=_headers(token)).status_code == 401
    # But a fresh login issues a working token.
    resp = client.post(
        "/auth/login", json={"email": "ana@example.com", "password": "nueva12345"}
    )
    assert resp.status_code == 200
    fresh = resp.json()["accessToken"]
    assert client.get("/auth/me", headers=_headers(fresh)).status_code == 200


def test_refresh_renews_expired_unrevoked_token(client):
    with freeze_time(FROZEN, tz_offset=0):
        data = _register(client)
        token = data["accessToken"]
    # The access token is now past its 15-min life but its refresh row is not.
    later = "2026-08-15 12:20:00"
    with freeze_time(later, tz_offset=0):
        resp = client.post(
            "/auth/refresh", json={"accessToken": token}
        )
        assert resp.status_code == 200
        new_token = resp.json()["accessToken"]
        # The renewed token works right now.
        assert client.get("/auth/me", headers=_headers(new_token)).status_code == 200
        # Rotation: replaying the old token must now fail.
        resp = client.post("/auth/refresh", json={"accessToken": token})
        assert resp.status_code == 401


def test_refresh_rejects_revoked_token(client):
    data = _register(client)
    token = data["accessToken"]
    client.post(
        "/auth/change-password",
        json={"currentPassword": "password123", "newPassword": "nueva12345"},
        headers=_headers(token),
    )
    # Even if the token is still inside its access-life, revocation wins.
    resp = client.post("/auth/refresh", json={"accessToken": token})
    assert resp.status_code == 401


def test_refresh_rejects_legacy_token_without_jti(client, session):
    from sqlalchemy import select

    _register(client)
    user = session.scalar(select(User).where(User.email == "ana@example.com"))
    legacy = _forge_token(user.id)  # no jti, as pre-deploy / fixtures
    assert client.get("/auth/me", headers=_headers(legacy)).status_code == 200
    resp = client.post("/auth/refresh", json={"accessToken": legacy})
    assert resp.status_code == 401


def test_forged_token_without_refresh_row_is_rejected(client, session):
    from sqlalchemy import select

    data = _register(client)
    user = session.scalar(select(User).where(User.email == "ana@example.com"))
    # A validly-signed token whose jti has no refresh_tokens row.
    forged = _forge_token(user.id, with_jti="deadbeef" * 4)
    assert client.get("/auth/me", headers=_headers(forged)).status_code == 401


def test_remove_member_revokes_expelled_sessions(client, session):
    from sqlalchemy import select

    from app.models import Account, Household

    owner = _register(client, email="owner@example.com", name="Owner")
    owner_tok = owner["accessToken"]
    # Second user joins via invitation.
    inv = client.post("/households/me/invitations", headers=_headers(owner_tok))
    assert inv.status_code == 201
    join_token = inv.json()["token"]
    join = client.post(
        "/auth/join",
        json={
            "token": join_token,
            "email": "member@example.com",
            "password": "password123",
            "name": "Member",
        },
    )
    assert join.status_code == 201
    member_tok = join.json()["accessToken"]
    member_id = client.get("/auth/me", headers=_headers(member_tok)).json()["id"]
    assert client.get("/auth/me", headers=_headers(member_tok)).status_code == 200

    # Owner expels the member (member has no personal accounts, so allowed).
    resp = client.delete(
        f"/households/me/members/{member_id}", headers=_headers(owner_tok)
    )
    assert resp.status_code == 204
    # The expelled member's session is revoked.
    assert client.get("/auth/me", headers=_headers(member_tok)).status_code == 401
    # And they cannot renew it either.
    assert (
        client.post("/auth/refresh", json={"accessToken": member_tok}).status_code
        == 401
    )


def test_refresh_window_expiry_revokes(client, session):
    with freeze_time(FROZEN, tz_offset=0):
        data = _register(client)
        token = data["accessToken"]
    # Force the refresh window to have elapsed (30 days + 1 day later).
    past = "2026-09-16 12:00:00"
    with freeze_time(past, tz_offset=0):
        assert client.get("/auth/me", headers=_headers(token)).status_code == 401
        resp = client.post("/auth/refresh", json={"accessToken": token})
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Issue #34: cookie httpOnly + token_identifier (jti) en la respuesta.
# ---------------------------------------------------------------------------


def _set_cookie_header(resp) -> str:
    """Concatena los valores del header set-cookie (puede repetirse)."""
    return "; ".join(resp.headers.get_list("set-cookie"))


def test_register_returns_token_identifier_and_sets_cookie(client):
    resp = client.post(
        "/auth/register",
        json={"email": "ana@example.com", "password": "password123", "name": "Ana", "householdName": "Hogar Ana"},
    )
    assert resp.status_code == 201
    data = resp.json()
    token = data["accessToken"]
    # token_identifier expone el jti del token emitido (el SPA lo compara).
    assert data["tokenIdentifier"]
    payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    assert data["tokenIdentifier"] == payload["jti"]
    # Cookie httpOnly con el JWT y atributos anti-XSS/CSRF (issue #34).
    set_cookie = _set_cookie_header(resp)
    assert "ff_token=" in set_cookie
    assert "HttpOnly" in set_cookie
    assert "SameSite=lax" in set_cookie
    assert "Path=/" in set_cookie


def test_cookie_authenticates_without_bearer_header(client):
    data = _register(client)
    token = data["accessToken"]
    client.cookies.set(settings.session_cookie_name, token)
    # Sin header Authorization: la cookie httpOnly autenticas sola.
    resp = client.get("/auth/me")
    assert resp.status_code == 200
    assert resp.json()["email"] == "ana@example.com"


def test_bearer_header_still_authenticates(client):
    # Back-compat: el header Bearer sigue siendo la vía principal.
    data = _register(client)
    assert client.get("/auth/me", headers=_headers(data["accessToken"])).status_code == 200


def test_login_sets_cookie(client):
    _register(client)
    resp = client.post("/auth/login", json={"email": "ana@example.com", "password": "password123"})
    assert resp.status_code == 200
    assert "ff_token=" in _set_cookie_header(resp)


def test_refresh_reads_token_from_cookie_when_no_body(client):
    # Issue #34: el SPA no puede leer el JWT (cookie httpOnly), así que el
    # refresh toma el token del cookie, no del body.
    with freeze_time(FROZEN, tz_offset=0):
        data = _register(client)
        token = data["accessToken"]
        old_jti = data["tokenIdentifier"]
    later = "2026-08-15 12:20:00"
    with freeze_time(later, tz_offset=0):
        client.cookies.set(settings.session_cookie_name, token)
        resp = client.post("/auth/refresh")  # sin body
        assert resp.status_code == 200
        new = resp.json()
        assert new["tokenIdentifier"] != old_jti
        assert "ff_token=" in _set_cookie_header(resp)
        # La cookie renovada (el token nuevo en la respuesta) autenticas.
        client.cookies.set(settings.session_cookie_name, new["accessToken"])
        assert client.get("/auth/me").status_code == 200
        # El token viejo quedó rotado: ya no sirve.
        client.cookies.set(settings.session_cookie_name, token)
        assert client.get("/auth/me").status_code == 401


def test_refresh_sets_cookie_and_new_identifier(client):
    with freeze_time(FROZEN, tz_offset=0):
        data = _register(client)
        token = data["accessToken"]
        old_jti = data["tokenIdentifier"]
    later = "2026-08-15 12:20:00"
    with freeze_time(later, tz_offset=0):
        resp = client.post("/auth/refresh", json={"accessToken": token})
        assert resp.status_code == 200
        new = resp.json()
        assert new["tokenIdentifier"] != old_jti  # rotación: jti distinto
        assert "ff_token=" in _set_cookie_header(resp)


def test_change_password_clears_cookie(client):
    data = _register(client)
    token = data["accessToken"]
    resp = client.post(
        "/auth/change-password",
        json={"currentPassword": "password123", "newPassword": "nueva12345"},
        headers=_headers(token),
    )
    assert resp.status_code == 204
    # La cookie debe borrarse (max-age=0 / expires en el pasado).
    set_cookie = _set_cookie_header(resp)
    assert "ff_token" in set_cookie
    assert "max-age=0" in set_cookie.lower()


def test_logout_clears_cookie_and_revokes(client):
    data = _register(client)
    token = data["accessToken"]
    client.cookies.set(settings.session_cookie_name, token)
    # Mientras el token vive, /auth/me con la cookie funciona.
    assert client.get("/auth/me").status_code == 200
    # El SPA no envía Bearer (auth por cookie): el logout revoca por cookie.
    resp = client.post("/auth/logout")
    assert resp.status_code == 204
    set_cookie = _set_cookie_header(resp)
    assert "ff_token" in set_cookie
    assert "max-age=0" in set_cookie.lower()
    # El jti queda revocado: ni con header ni con cookie el token ya sirve.
    assert client.get("/auth/me", headers=_headers(token)).status_code == 401
    client.cookies.set(settings.session_cookie_name, token)
    assert client.get("/auth/me").status_code == 401
