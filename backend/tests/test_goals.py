"""Metas de ahorro: CRUD, aportes manuales y aislamiento por hogar."""

from datetime import date, datetime, timedelta, timezone

import jwt
import pytest

from app.config import settings
from app.models import Account, Household, SavingsGoal, User


def make_headers(user: User) -> dict[str, str]:
    token = jwt.encode(
        {"sub": user.id, "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(name="world")
def world_fixture(session):
    u1 = User(email="uno@example.com", hashed_password="x", name="Uno")
    u2 = User(email="dos@example.com", hashed_password="x", name="Dos")
    session.add_all([u1, u2])
    session.flush()
    h1 = Household(name="Hogar Uno", owner_id=u1.id)
    h2 = Household(name="Hogar Dos", owner_id=u2.id)
    session.add_all([h1, h2])
    session.flush()
    u1.household_id, u2.household_id = h1.id, h2.id
    a1 = Account(household_id=h1.id, name="Ahorro", kind="savings", opening_balance=0)
    a2 = Account(household_id=h2.id, name="Ahorro ajeno", kind="savings", opening_balance=0)
    session.add_all([a1, a2])
    session.commit()
    return {"h1": h1, "h2": h2, "u1": u1, "u2": u2, "a1": a1, "a2": a2, "headers1": make_headers(u1), "headers2": make_headers(u2)}


def create_goal(client, world, **overrides):
    payload = {
        "name": "Vacaciones",
        "targetAmount": 1000,
        "currentAmount": 200,
        "targetDate": "2026-12-31",
        "accountId": world["a1"].id,
        "icon": "piggy-bank",
        "color": "#30b0c7",
    } | overrides
    return client.post("/goals", json=payload, headers=world["headers1"])


def test_create_list_and_update_goal(client, world):
    created = create_goal(client, world)
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["householdId"] == world["h1"].id
    assert body["progressPct"] == 20
    assert body["remaining"] == 800
    assert not body["isCompleted"]

    listed = client.get("/goals", headers=world["headers1"])
    assert [goal["id"] for goal in listed.json()] == [body["id"]]

    updated = client.patch(
        f"/goals/{body['id']}",
        json={"name": "Viaje", "targetAmount": 500, "archived": True},
        headers=world["headers1"],
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Viaje"
    assert updated.json()["archived"] is True
    assert updated.json()["progressPct"] == 40


def test_contribution_accepts_negative_and_caps_computed_values(client, world):
    goal = create_goal(client, world).json()
    added = client.post(
        f"/goals/{goal['id']}/contribute", json={"amount": 900}, headers=world["headers1"]
    )
    assert added.status_code == 200
    assert added.json()["currentAmount"] == 1100
    assert added.json()["progressPct"] == 100
    assert added.json()["remaining"] == 0
    assert added.json()["isCompleted"] is True

    withdrawn = client.post(
        f"/goals/{goal['id']}/contribute", json={"amount": -150}, headers=world["headers1"]
    )
    assert withdrawn.status_code == 200
    assert withdrawn.json()["currentAmount"] == 950
    assert withdrawn.json()["progressPct"] == 95
    assert withdrawn.json()["remaining"] == 50


def test_goal_rejects_zero_contribution_and_foreign_account(client, world):
    goal = create_goal(client, world).json()
    zero = client.post(
        f"/goals/{goal['id']}/contribute", json={"amount": 0}, headers=world["headers1"]
    )
    assert zero.status_code == 422
    foreign = create_goal(client, world, accountId=world["a2"].id)
    assert foreign.status_code == 422


@pytest.mark.parametrize("field", ["name", "targetAmount", "icon", "color", "archived"])
def test_update_rejects_null_for_non_nullable_fields(client, world, field):
    goal = create_goal(client, world).json()
    response = client.patch(
        f"/goals/{goal['id']}", json={field: None}, headers=world["headers1"]
    )
    assert response.status_code == 422


def test_update_accepts_null_for_optional_fields(client, world):
    goal = create_goal(client, world).json()
    response = client.patch(
        f"/goals/{goal['id']}",
        json={"targetDate": None, "accountId": None},
        headers=world["headers1"],
    )
    assert response.status_code == 200
    assert response.json()["targetDate"] is None
    assert response.json()["accountId"] is None


@pytest.mark.parametrize("invalid_amount", ["NaN", "Infinity", "1.00001", "1000000000000000"])
def test_create_rejects_nonfinite_or_out_of_range_money(client, world, invalid_amount):
    for field in ("targetAmount", "currentAmount"):
        response = create_goal(client, world, **{field: invalid_amount})
        assert response.status_code == 422


@pytest.mark.parametrize("invalid_amount", ["NaN", "Infinity", "1.00001", "1000000000000000"])
def test_update_rejects_nonfinite_or_out_of_range_target(client, world, invalid_amount):
    goal = create_goal(client, world).json()
    response = client.patch(
        f"/goals/{goal['id']}",
        json={"targetAmount": invalid_amount},
        headers=world["headers1"],
    )
    assert response.status_code == 422


@pytest.mark.parametrize("invalid_amount", ["NaN", "Infinity", "0.00001", "1000000000000000"])
def test_contribution_rejects_nonfinite_or_out_of_range_money(client, world, invalid_amount):
    goal = create_goal(client, world).json()
    response = client.post(
        f"/goals/{goal['id']}/contribute",
        json={"amount": invalid_amount},
        headers=world["headers1"],
    )
    assert response.status_code == 422


def test_contribution_cannot_overflow_numeric_range(client, world):
    goal = create_goal(client, world, currentAmount="999999999999999.9999").json()
    response = client.post(
        f"/goals/{goal['id']}/contribute", json={"amount": 1}, headers=world["headers1"]
    )
    assert response.status_code == 422


def test_goals_are_isolated_and_can_be_deleted(client, world):
    goal = create_goal(client, world).json()
    assert client.get("/goals", headers=world["headers2"]).json() == []
    for method, kwargs in [("patch", {"json": {"archived": True}}), ("post", {"json": {"amount": 1}}), ("delete", {})]:
        path = f"/goals/{goal['id']}" + ("/contribute" if method == "post" else "")
        response = getattr(client, method)(path, headers=world["headers2"], **kwargs)
        assert response.status_code == 404
    deleted = client.delete(f"/goals/{goal['id']}", headers=world["headers1"])
    assert deleted.status_code == 204
    assert client.get("/goals", headers=world["headers1"]).json() == []


def test_account_deletion_unlinks_goal(client, session, world):
    goal = SavingsGoal(
        household_id=world["h1"].id,
        name="Fondo",
        target_amount=100,
        current_amount=0,
        account_id=world["a1"].id,
        target_date=date.today(),
        icon="piggy-bank",
        color="#30b0c7",
    )
    session.add(goal)
    session.commit()
    deleted = client.delete(f"/accounts/{world['a1'].id}", headers=world["headers1"])
    assert deleted.status_code == 204
    session.refresh(goal)
    assert goal.account_id is None
