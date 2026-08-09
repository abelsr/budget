"""A divided purchase remains one ledger movement with category allocations."""

from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app.config import settings
from app.models import Household, User


def _headers(user: User) -> dict[str, str]:
    token = jwt.encode(
        {"sub": user.id, "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(name="split_world")
def split_world_fixture(client, session):
    user = User(email="splits@example.com", hashed_password="x", name="Ana")
    session.add(user)
    session.flush()
    household = Household(name="Casa", owner_id=user.id)
    session.add(household)
    session.flush()
    user.household_id = household.id
    session.commit()
    headers = _headers(user)
    account = client.post("/accounts", json={"name": "Débito", "kind": "debit", "openingBalance": 500}, headers=headers).json()

    def category(name: str, tx_type: str = "expense") -> dict:
        response = client.post("/categories", json={"name": name, "icon": "tag", "color": "#30b0c7", "type": tx_type}, headers=headers)
        assert response.status_code == 201, response.text
        return response.json()

    return {
        "headers": headers,
        "account": account,
        "food": category("Comida"),
        "home": category("Hogar"),
        "income": category("Sueldo", "income"),
    }


def _payload(world, **overrides):
    payload = {
        "type": "expense",
        "amount": 125,
        "accountId": world["account"]["id"],
        "date": "2026-08-08",
        "note": "Supermercado",
        "splits": [
            {"categoryId": world["food"]["id"], "amount": 100},
            {"categoryId": world["home"]["id"], "amount": 25},
        ],
    }
    payload.update(overrides)
    return payload


def test_split_creates_one_ledger_row_and_allocates_budgets(client, split_world):
    world = split_world
    response = client.post("/transactions", json=_payload(world), headers=world["headers"])
    assert response.status_code == 201, response.text
    movement = response.json()
    assert movement["isSplit"] is True
    assert movement["categoryId"] is None
    assert {(split["categoryId"], split["amount"]) for split in movement["splits"]} == {
        (world["food"]["id"], 100.0), (world["home"]["id"], 25.0)
    }
    assert len(client.get("/transactions", headers=world["headers"]).json()) == 1
    assert client.get("/accounts", headers=world["headers"]).json()[0]["balance"] == 375.0

    for category, amount in ((world["food"], 200), (world["home"], 50)):
        assert client.post("/budgets", json={"categoryId": category["id"], "amount": amount}, headers=world["headers"]).status_code == 201
    status = {row["categoryId"]: row["spent"] for row in client.get("/budgets/status?month=2026-08", headers=world["headers"]).json()}
    assert status == {world["food"]["id"]: 100.0, world["home"]["id"]: 25.0}


def test_split_is_filterable_and_does_not_double_count_summary(client, split_world):
    world = split_world
    assert client.post("/transactions", json=_payload(world), headers=world["headers"]).status_code == 201
    filtered = client.get(f"/transactions?categoryId={world['home']['id']}", headers=world["headers"])
    assert filtered.status_code == 200
    assert len(filtered.json()) == 1
    summary = client.get("/summary/month?month=2026-08", headers=world["headers"]).json()
    assert summary["expense"] == 125.0
    assert {row["categoryId"]: row["total"] for row in summary["byCategory"]} == {
        world["food"]["id"]: 100.0, world["home"]["id"]: 25.0
    }


@pytest.mark.parametrize("splits", [
    [{"categoryId": "food", "amount": 125}],
    [{"categoryId": "food", "amount": 100}, {"categoryId": "home", "amount": 20}],
    [{"categoryId": "food", "amount": 50}, {"categoryId": "food", "amount": 75}],
])
def test_split_requires_two_distinct_exact_allocations(client, split_world, splits):
    world = split_world
    categories = {"food": world["food"]["id"], "home": world["home"]["id"]}
    response = client.post(
        "/transactions",
        json=_payload(world, splits=[{**split, "categoryId": categories[split["categoryId"]]} for split in splits]),
        headers=world["headers"],
    )
    assert response.status_code == 422


def test_split_update_replaces_allocations_or_converts_to_simple(client, split_world):
    world = split_world
    movement = client.post("/transactions", json=_payload(world), headers=world["headers"]).json()
    updated = client.patch(
        f"/transactions/{movement['id']}",
        json={"amount": 150, "splits": [
            {"categoryId": world["food"]["id"], "amount": 90},
            {"categoryId": world["home"]["id"], "amount": 60},
        ]},
        headers=world["headers"],
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["amount"] == 150.0
    simple = client.patch(
        f"/transactions/{movement['id']}",
        json={"categoryId": world["food"]["id"], "splits": []},
        headers=world["headers"],
    )
    assert simple.status_code == 200, simple.text
    assert simple.json()["isSplit"] is False
    assert simple.json()["splits"] == []


def test_split_rejects_wrong_category_type_and_recurring(client, split_world):
    world = split_world
    wrong_type = client.post(
        "/transactions",
        json=_payload(world, splits=[
            {"categoryId": world["food"]["id"], "amount": 100},
            {"categoryId": world["income"]["id"], "amount": 25},
        ]),
        headers=world["headers"],
    )
    assert wrong_type.status_code == 422
    recurring = client.post("/transactions", json=_payload(world, repeat="monthly"), headers=world["headers"])
    assert recurring.status_code == 422
