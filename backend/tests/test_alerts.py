from datetime import date, datetime, timedelta, timezone

import jwt
import pytest

from app.config import settings
from app.models import Account, Budget, Category, Household, RecurringRule, SavingsGoal, Transaction, User


def headers_for(user: User) -> dict[str, str]:
    token = jwt.encode(
        {"sub": user.id, "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(name="world")
def world_fixture(session):
    user = User(email="alerts@example.com", hashed_password="x", name="Alertas")
    other = User(email="other-alerts@example.com", hashed_password="x", name="Otro")
    session.add_all([user, other])
    session.flush()
    household = Household(name="Hogar alertas", owner_id=user.id)
    other_household = Household(name="Otro hogar", owner_id=other.id)
    session.add_all([household, other_household])
    session.flush()
    user.household_id = household.id
    other.household_id = other_household.id
    account = Account(household_id=household.id, name="Débito", kind="debit", opening_balance=-10)
    category = Category(household_id=household.id, name="Comida", icon="pizza", color="#30b0c7", type="expense")
    session.add_all([account, category])
    session.commit()
    return {"user": user, "other": other, "household": household, "account": account, "category": category, "headers": headers_for(user), "other_headers": headers_for(other)}


def test_alerts_generate_once_read_and_remain_isolated(client, session, world):
    today = date.today()
    session.add_all([
        Budget(household_id=world["household"].id, category_id=world["category"].id, amount=100),
        Transaction(household_id=world["household"].id, type="expense", amount=110, category_id=world["category"].id, account_id=world["account"].id, member_id=world["user"].id, date=today),
        RecurringRule(household_id=world["household"].id, type="expense", amount=20, category_id=world["category"].id, account_id=world["account"].id, created_by_id=world["user"].id, frequency="weekly", next_run_date=today - timedelta(days=4), anchor_day=None),
        SavingsGoal(household_id=world["household"].id, name="Viaje", target_amount=100, current_amount=100, icon="piggy-bank", color="#30b0c7"),
    ])
    session.commit()

    first = client.get("/alerts", headers=world["headers"])
    assert first.status_code == 200, first.text
    alerts = first.json()
    assert {alert["kind"] for alert in alerts} == {"budget_warning", "budget_exceeded", "recurring_overdue", "goal_reached", "negative_balance"}
    assert client.get("/alerts", headers=world["headers"]).json() == alerts
    assert client.get("/alerts", headers=world["other_headers"]).json() == []

    budget_alert = next(alert for alert in alerts if alert["kind"] == "budget_exceeded")
    assert client.post("/alerts/read", json={"alertId": budget_alert["id"]}, headers=world["headers"]).status_code == 200
    after_read = client.get("/alerts", headers=world["headers"]).json()
    assert next(alert for alert in after_read if alert["id"] == budget_alert["id"])["readAt"] is not None


def test_overdue_alert_generates_the_pending_rule(client, session, world):
    rule = RecurringRule(household_id=world["household"].id, type="expense", amount=20, category_id=world["category"].id, account_id=world["account"].id, created_by_id=world["user"].id, frequency="weekly", next_run_date=date.today() - timedelta(days=4), anchor_day=None)
    session.add(rule)
    session.commit()

    alerts = client.get("/alerts", headers=world["headers"]).json()
    alert = next(alert for alert in alerts if alert["kind"] == "recurring_overdue")
    generated = client.post(f"/alerts/{alert['id']}/generate", headers=world["headers"])
    assert generated.status_code == 200, generated.text
    assert generated.json()["generated"] == 1
    after_generate = client.get("/alerts", headers=world["headers"]).json()
    assert next(item for item in after_generate if item["id"] == alert["id"])["readAt"] is not None
