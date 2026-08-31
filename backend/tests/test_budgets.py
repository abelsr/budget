"""Presupuestos: CRUD, unicidad por categoría, y /budgets/status contra
transacciones reales del mes."""

from datetime import date

import pytest
from sqlalchemy import select

from app.models import Budget, Transaction


@pytest.fixture(name="world")
def world_fixture(world_factory):
    """Dos hogares, cada uno con cuenta + categoría de gasto + de ingreso."""
    return world_factory(
        accounts=(
            {"household": 1, "name": "Débito", "kind": "debit", "opening_balance": 0},
            {"household": 2, "name": "Débito", "kind": "debit", "opening_balance": 0},
        ),
        categories=(
            {"household": 1, "name": "Comida", "icon": "pizza", "color": "#30b0c7", "type": "expense"},
            {"household": 1, "name": "Salario", "icon": "briefcase", "color": "#00ff00", "type": "income"},
            {"household": 2, "name": "Comida", "icon": "pizza", "color": "#30b0c7", "type": "expense"},
        ),
    )


def _add_transaction(session, *, household, account, category, member, tx_type, amount, tx_date):
    tx = Transaction(
        household_id=household.id,
        type=tx_type,
        amount=amount,
        category_id=category.id,
        account_id=account.id,
        member_id=member.id,
        date=tx_date,
    )
    session.add(tx)
    return tx


# ---------- CRUD ----------


def test_create_and_list_budget(client, world):
    resp = client.post(
        "/budgets",
        json={"categoryId": world["categories"][0].id, "amount": 1500.0},
        headers=world["headers1"],
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["categoryId"] == world["categories"][0].id
    assert body["amount"] == 1500.0
    assert body["householdId"] == world["h1"].id
    assert body["month"] is None
    assert body["rollover"] is False

    listed = client.get("/budgets", headers=world["headers1"])
    assert listed.status_code == 200
    assert [b["id"] for b in listed.json()] == [body["id"]]


def test_create_budget_on_income_category_rejected(client, world):
    resp = client.post(
        "/budgets",
        json={"categoryId": world["categories"][1].id, "amount": 500.0},
        headers=world["headers1"],
    )
    assert resp.status_code == 422


def test_create_duplicate_budget_conflicts(client, world):
    payload = {"categoryId": world["categories"][0].id, "amount": 1000.0}
    first = client.post("/budgets", json=payload, headers=world["headers1"])
    assert first.status_code == 201
    second = client.post("/budgets", json=payload, headers=world["headers1"])
    assert second.status_code == 409


def test_monthly_budget_coexists_with_global_default_and_takes_precedence(freeze_time, client, world):
    global_budget = client.post(
        "/budgets",
        json={"categoryId": world["categories"][0].id, "amount": 100.0},
        headers=world["headers1"],
    )
    assert global_budget.status_code == 201
    monthly = client.post(
        "/budgets",
        json={
            "categoryId": world["categories"][0].id,
            "amount": 250.0,
            "month": "2026-08-28",
            "rollover": True,
        },
        headers=world["headers1"],
    )
    assert monthly.status_code == 201, monthly.text
    assert monthly.json()["month"] == "2026-08-01"

    status = client.get("/budgets/status?month=2026-08", headers=world["headers1"])
    assert status.status_code == 200
    assert status.json() == [
        {
            "categoryId": world["categories"][0].id,
            "budget": 250.0,
            "available": 250.0,
            "spent": 0.0,
            "percentage": 0.0,
        }
    ]


def test_duplicate_monthly_budget_conflicts_but_another_month_is_allowed(client, world):
    payload = {"categoryId": world["categories"][0].id, "amount": 100.0, "month": "2026-08-01"}
    assert client.post("/budgets", json=payload, headers=world["headers1"]).status_code == 201
    assert client.post("/budgets", json=payload, headers=world["headers1"]).status_code == 409
    assert client.post(
        "/budgets",
        json={**payload, "month": "2026-09-01"},
        headers=world["headers1"],
    ).status_code == 201


def test_update_budget_amount(client, world):
    created = client.post(
        "/budgets",
        json={"categoryId": world["categories"][0].id, "amount": 1000.0},
        headers=world["headers1"],
    ).json()
    resp = client.patch(
        f"/budgets/{created['id']}", json={"amount": 2000.0}, headers=world["headers1"]
    )
    assert resp.status_code == 200
    assert resp.json()["amount"] == 2000.0


def test_delete_budget(client, world):
    created = client.post(
        "/budgets",
        json={"categoryId": world["categories"][0].id, "amount": 1000.0},
        headers=world["headers1"],
    ).json()
    resp = client.delete(f"/budgets/{created['id']}", headers=world["headers1"])
    assert resp.status_code == 204
    assert client.get("/budgets", headers=world["headers1"]).json() == []


def test_cross_household_access_is_404(client, world):
    created = client.post(
        "/budgets",
        json={"categoryId": world["categories"][0].id, "amount": 1000.0},
        headers=world["headers1"],
    ).json()
    for verb, kwargs in [
        ("patch", {"json": {"amount": 1.0}}),
        ("delete", {}),
    ]:
        resp = getattr(client, verb)(
            f"/budgets/{created['id']}", headers=world["headers2"], **kwargs
        )
        assert resp.status_code == 404


def test_budgets_list_is_isolated_per_household(client, world):
    client.post(
        "/budgets",
        json={"categoryId": world["categories"][0].id, "amount": 1000.0},
        headers=world["headers1"],
    )
    assert client.get("/budgets", headers=world["headers2"]).json() == []


# ---------- /budgets/status ----------


def test_status_computes_spent_and_percentage(freeze_time, client, session, world):
    client.post(
        "/budgets",
        json={"categoryId": world["categories"][0].id, "amount": 200.0},
        headers=world["headers1"],
    )
    today = date.today()
    day = date(today.year, today.month, 10)
    _add_transaction(
        session, household=world["h1"], account=world["account1"], category=world["categories"][0],
        member=world["u1"], tx_type="expense", amount=150.0, tx_date=day,
    )
    session.commit()

    resp = client.get("/budgets/status", headers=world["headers1"])
    assert resp.status_code == 200
    rows = resp.json()
    assert len(rows) == 1
    assert rows[0]["categoryId"] == world["categories"][0].id
    assert rows[0]["budget"] == 200.0
    assert rows[0]["spent"] == 150.0
    assert rows[0]["percentage"] == 75.0


def test_status_ignores_income_in_same_category_scope(freeze_time, client, session, world):
    """Un ingreso no debe sumar al gasto, aun si por error compartiera categoría."""
    client.post(
        "/budgets",
        json={"categoryId": world["categories"][0].id, "amount": 200.0},
        headers=world["headers1"],
    )
    today = date.today()
    day = date(today.year, today.month, 5)
    _add_transaction(
        session, household=world["h1"], account=world["account1"], category=world["categories"][0],
        member=world["u1"], tx_type="income", amount=999.0, tx_date=day,
    )
    session.commit()

    resp = client.get("/budgets/status", headers=world["headers1"])
    assert resp.json()[0]["spent"] == 0.0


def test_status_different_month_resets_without_recreating_budget(freeze_time, client, session, world):
    budget = client.post(
        "/budgets",
        json={"categoryId": world["categories"][0].id, "amount": 200.0},
        headers=world["headers1"],
    ).json()
    today = date.today()
    _add_transaction(
        session, household=world["h1"], account=world["account1"], category=world["categories"][0],
        member=world["u1"], tx_type="expense", amount=150.0, tx_date=date(today.year, today.month, 10),
    )
    session.commit()

    resp = client.get("/budgets/status", params={"month": "2000-01"}, headers=world["headers1"])
    assert resp.status_code == 200
    rows = resp.json()
    assert rows[0]["spent"] == 0.0
    assert rows[0]["budget"] == 200.0

    # El presupuesto sigue siendo el mismo registro, no uno nuevo por mes.
    assert client.get("/budgets", headers=world["headers1"]).json()[0]["id"] == budget["id"]


@pytest.mark.parametrize(
    ("rollover", "previous_spend", "expected_available"),
    [(False, 40.0, 100.0), (True, 40.0, 160.0), (True, 120.0, 100.0)],
)
def test_status_rollover_uses_only_previous_month_surplus(
    client, session, world, rollover, previous_spend, expected_available
):
    created = client.post(
        "/budgets",
        json={
            "categoryId": world["categories"][0].id,
            "amount": 100.0,
            "rollover": rollover,
        },
        headers=world["headers1"],
    )
    assert created.status_code == 201
    _add_transaction(
        session,
        household=world["h1"],
        account=world["account1"],
        category=world["categories"][0],
        member=world["u1"],
        tx_type="expense",
        amount=previous_spend,
        tx_date=date(2025, 12, 10),
    )
    _add_transaction(
        session,
        household=world["h1"],
        account=world["account1"],
        category=world["categories"][0],
        member=world["u1"],
        tx_type="expense",
        amount=80.0,
        tx_date=date(2026, 1, 10),
    )
    session.commit()

    status = client.get("/budgets/status?month=2026-01", headers=world["headers1"])
    assert status.status_code == 200
    assert status.json()[0]["available"] == expected_available
    assert status.json()[0]["spent"] == 80.0
    assert status.json()[0]["percentage"] == round(80 / expected_available * 100, 1)


def test_status_is_empty_without_budgets(client, world):
    resp = client.get("/budgets/status", headers=world["headers1"])
    assert resp.status_code == 200
    assert resp.json() == []


def test_status_is_isolated_between_households(freeze_time, client, session, world):
    client.post(
        "/budgets",
        json={"categoryId": world["categories"][0].id, "amount": 200.0},
        headers=world["headers1"],
    )
    today = date.today()
    day = date(today.year, today.month, 10)
    _add_transaction(
        session, household=world["h2"], account=world["account2"], category=world["categories"][2],
        member=world["u2"], tx_type="expense", amount=9999.0, tx_date=day,
    )
    session.commit()

    resp = client.get("/budgets/status", headers=world["headers2"])
    assert resp.json() == []


# ---------- Interacción con categorías ----------


def test_deleting_category_with_budget_cascades(client, session, world):
    client.post(
        "/budgets",
        json={"categoryId": world["categories"][0].id, "amount": 200.0},
        headers=world["headers1"],
    )
    resp = client.delete(f"/categories/{world['categories'][0].id}", headers=world["headers1"])
    assert resp.status_code == 204
    remaining = session.scalars(
        select(Budget).where(Budget.category_id == world["categories"][0].id)
    ).all()
    assert remaining == []
    assert client.get("/budgets/status", headers=world["headers1"]).json() == []
