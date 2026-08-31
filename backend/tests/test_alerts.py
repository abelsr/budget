from datetime import date, timedelta

import pytest

from app.models import Account, Budget, Category, Household, RecurringRule, SavingsGoal, Transaction, User
from tests.helpers import auth_headers


@pytest.fixture(name="world")
def world_fixture(world_factory):
    return world_factory(
        emails=("alerts@example.com", "other-alerts@example.com"),
        names=("Alertas", "Otro"),
        household_names=("Hogar alertas", "Otro hogar"),
        accounts=(
            {"household": 1, "name": "Débito", "kind": "debit", "opening_balance": -10},
        ),
        categories=(
            {"household": 1, "name": "Comida", "icon": "pizza", "color": "#30b0c7", "type": "expense"},
        ),
    )


def test_alerts_generate_once_read_and_remain_isolated(freeze_time, client, session, world):
    today = date.today()
    session.add_all([
        Budget(household_id=world["h1"].id, category_id=world["categories"][0].id, amount=100),
        Transaction(household_id=world["h1"].id, type="expense", amount=110, category_id=world["categories"][0].id, account_id=world["account1"].id, member_id=world["u1"].id, date=today),
        RecurringRule(household_id=world["h1"].id, type="expense", amount=20, category_id=world["categories"][0].id, account_id=world["account1"].id, created_by_id=world["u1"].id, frequency="weekly", next_run_date=today - timedelta(days=4), anchor_day=None),
        SavingsGoal(household_id=world["h1"].id, name="Viaje", target_amount=100, current_amount=100, icon="piggy-bank", color="#30b0c7"),
    ])
    session.commit()

    first = client.get("/alerts", headers=world["headers1"])
    assert first.status_code == 200, first.text
    alerts = first.json()
    assert {alert["kind"] for alert in alerts} == {"budget_warning", "budget_exceeded", "recurring_overdue", "goal_reached", "negative_balance"}
    assert client.get("/alerts", headers=world["headers1"]).json() == alerts
    assert client.get("/alerts", headers=world["headers2"]).json() == []

    budget_alert = next(alert for alert in alerts if alert["kind"] == "budget_exceeded")
    assert client.post("/alerts/read", json={"alertId": budget_alert["id"]}, headers=world["headers1"]).status_code == 200
    after_read = client.get("/alerts", headers=world["headers1"]).json()
    assert next(alert for alert in after_read if alert["id"] == budget_alert["id"])["readAt"] is not None


def test_overdue_alert_generates_the_pending_rule(freeze_time, client, session, world):
    rule = RecurringRule(household_id=world["h1"].id, type="expense", amount=20, category_id=world["categories"][0].id, account_id=world["account1"].id, created_by_id=world["u1"].id, frequency="weekly", next_run_date=date.today() - timedelta(days=4), anchor_day=None)
    session.add(rule)
    session.commit()

    alerts = client.get("/alerts", headers=world["headers1"]).json()
    alert = next(alert for alert in alerts if alert["kind"] == "recurring_overdue")
    generated = client.post(f"/alerts/{alert['id']}/generate", headers=world["headers1"])
    assert generated.status_code == 200, generated.text
    assert generated.json()["generated"] == 1
    after_generate = client.get("/alerts", headers=world["headers1"]).json()
    assert next(item for item in after_generate if item["id"] == alert["id"])["readAt"] is not None


# ---------- Card payment due and instalment due ----------


def _cycle_for_due(in_days: int) -> tuple[int, int]:
    """statement_day/payment_due_days such that the next payment due lands today+in_days."""
    from app.services.card_calendar import next_statement_date

    target = date.today() + timedelta(days=in_days)
    for statement_day in range(28, 0, -1):
        next_stmt = next_statement_date(statement_day, date.today())
        diff = (target - next_stmt).days
        if 1 <= diff <= 60:
            return statement_day, diff
    raise AssertionError("no cycle found for the target due date")


def _card_household(session):
    user = User(email="card@example.com", hashed_password="x", name="Card")
    session.add(user)
    session.flush()
    household = Household(name="Tarjetas", owner_id=user.id)
    session.add(household)
    session.flush()
    user.household_id = household.id
    category = Category(household_id=household.id, name="Hogar", icon="x", color="#000000", type="expense")
    card = Account(household_id=household.id, name="BBVA", kind="credit", opening_balance=0)
    session.add_all([category, card])
    session.commit()
    return user, household, category, card


def test_card_payment_due_alert_within_lead_days(freeze_time, client, session):
    user, household, category, card = _card_household(session)
    statement_day, due_days = _cycle_for_due(3)
    card.statement_day = statement_day
    card.payment_due_days = due_days
    session.add(
        Transaction(household_id=household.id, type="expense", amount=12000, category_id=category.id, account_id=card.id, member_id=user.id, date=date.today())
    )
    session.commit()
    headers = auth_headers(user)
    alerts = client.get("/alerts", headers=headers).json()
    card_alerts = [alert for alert in alerts if alert["kind"] == "card_payment_due"]
    assert len(card_alerts) == 1
    assert card_alerts[0]["payload"]["account_id"] == card.id
    assert card_alerts[0]["payload"]["estimated_amount"] == 12000.0
    # idempotent: a second read creates nothing new
    assert [alert for alert in client.get("/alerts", headers=headers).json() if alert["kind"] == "card_payment_due"] == card_alerts


def test_card_payment_due_not_before_lead_days(freeze_time, client, session):
    user, household, category, card = _card_household(session)
    statement_day, due_days = _cycle_for_due(4)
    card.statement_day = statement_day
    card.payment_due_days = due_days
    session.add(
        Transaction(household_id=household.id, type="expense", amount=12000, category_id=category.id, account_id=card.id, member_id=user.id, date=date.today())
    )
    session.commit()
    alerts = client.get("/alerts", headers=auth_headers(user)).json()
    assert [alert for alert in alerts if alert["kind"] == "card_payment_due"] == []


def test_instalment_due_alert_within_lead_days(freeze_time, client, session):
    from app.models import InstalmentPlan

    user, household, category, card = _card_household(session)
    session.add(
        Transaction(household_id=household.id, type="expense", amount=3000, category_id=category.id, account_id=card.id, member_id=user.id, date=date.today())
    )
    session.commit()
    purchase = session.query(Transaction).one()
    session.add(
        InstalmentPlan(
            household_id=household.id,
            account_id=card.id,
            source_transaction_id=purchase.id,
            months=3,
            total_amount=3000,
            monthly_amount=1000,
            first_due_date=date.today() + timedelta(days=2),
            created_by_id=user.id,
        )
    )
    session.commit()
    headers = auth_headers(user)
    alerts = client.get("/alerts", headers=headers).json()
    instalment_alerts = [alert for alert in alerts if alert["kind"] == "instalment_due"]
    assert len(instalment_alerts) == 1
    assert instalment_alerts[0]["payload"]["plan_id"] is not None
    # idempotent
    assert [alert for alert in client.get("/alerts", headers=headers).json() if alert["kind"] == "instalment_due"] == instalment_alerts
    # a paused plan with the same due date emits nothing new
    purchase2 = Transaction(household_id=household.id, type="expense", amount=1200, category_id=category.id, account_id=card.id, member_id=user.id, date=date.today())
    session.add(purchase2)
    session.flush()
    session.add(
        InstalmentPlan(
            household_id=household.id,
            account_id=card.id,
            source_transaction_id=purchase2.id,
            months=3,
            total_amount=1200,
            monthly_amount=400,
            first_due_date=date.today() + timedelta(days=2),
            created_by_id=user.id,
            status="paused",
        )
    )
    session.commit()
    assert [alert for alert in client.get("/alerts", headers=headers).json() if alert["kind"] == "instalment_due"] == instalment_alerts
