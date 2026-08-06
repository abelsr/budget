from datetime import date, datetime, timedelta, timezone

import jwt

from app.config import settings
from app.models import Category, Household, User

FAKE_PNG = b"\x89PNG\r\n\x1a\n....fake"


def _create_user_with_category(session):
    """Crea hogar + usuario + categoría expense activa y devuelve headers JWT."""
    user = User(
        email="tester@example.com",
        hashed_password="not-a-real-hash",
        name="Tester",
    )
    session.add(user)
    session.flush()
    household = Household(name="Familia Test", owner_id=user.id)
    session.add(household)
    session.flush()
    user.household_id = household.id
    category = Category(
        household_id=household.id,
        name="Supermercado",
        icon="shopping-cart",
        color="#30b0c7",
        type="expense",
        active=True,
    )
    session.add(category)
    session.commit()

    token = jwt.encode(
        {"sub": user.id, "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    return user, category, {"Authorization": f"Bearer {token}"}


def test_scan_without_openrouter_api_key_returns_501(client, session, monkeypatch):
    _, _, headers = _create_user_with_category(session)
    # Hermético: fuerza ausencia de key aunque exista en .env
    monkeypatch.setattr(settings, "openrouter_api_key", None)

    response = client.post(
        "/tickets/scan",
        files={"file": ("ticket.png", FAKE_PNG, "image/png")},
        headers=headers,
    )

    assert response.status_code == 501
    assert response.json() == {
        "detail": "Escáner no configurado: falta OPENROUTER_API_KEY"
    }


def test_scan_success_returns_camel_case(client, session, monkeypatch):
    _, category, headers = _create_user_with_category(session)

    async def fake_analyze(image_bytes, mime_type, categories):
        return {
            "merchant": "Walmart",
            "total": 1234.56,
            "date": date(2026, 7, 22),
            "suggested_category_id": category.id,
            "confidence": 0.95,
        }

    # Se parchea donde se USA (el símbolo importado en la ruta).
    monkeypatch.setattr("app.api.routes.tickets.analyze_ticket", fake_analyze)

    response = client.post(
        "/tickets/scan",
        files={"file": ("ticket.png", FAKE_PNG, "image/png")},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json() == {
        "merchant": "Walmart",
        "total": 1234.56,
        "date": "2026-07-22",
        "suggestedCategoryId": category.id,
        "confidence": 0.95,
    }


def test_scan_rejects_non_image_content_type(client, session):
    _, _, headers = _create_user_with_category(session)

    response = client.post(
        "/tickets/scan",
        files={"file": ("ticket.txt", b"hola", "text/plain")},
        headers=headers,
    )

    assert response.status_code == 415


def test_scan_without_token_returns_401(client, session):
    _create_user_with_category(session)

    response = client.post(
        "/tickets/scan",
        files={"file": ("ticket.png", FAKE_PNG, "image/png")},
    )

    assert response.status_code == 401
