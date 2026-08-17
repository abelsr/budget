"""Cash-flow forecast: opening balance, daily deltas, projected recurring
rules (without materializing), the upcoming-movements window, and the
read-only guarantee."""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import jwt
import pytest
from sqlalchemy import func, select

from app.config import settings
from app.models import Account, Category, Household, RecurringRule, Transaction, User
from app.services.forecast import build_forecast


def make_headers(user: User) -> dict[str, str]:
    token = jwt.encode(
        {"sub": user.id, "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(name="world")
def world_fixture(session):
    """Two isolated households; h1 with a shared account, a personal account
    and categories, h2 with the minimum to compare isolation."""
    u1 = User(email="uno@example.com", hashed_password="x", name="Uno")
    u2 = User(email="dos@example.com", hashed_password="x", name="Dos")
    session.add_all([u1, u2])
    session.flush()
    h1 = Household(name="Hogar Uno", owner_id=u1.id)
    h2 = Household(name="Hogar Dos", owner_id=u2.id)
    session.add_all([h1, h2])
    session.flush()
    u1.household_id = h1.id
    u2.household_id = h2.id
    session.commit()
    account1 = Account(household_id=h1.id, name="Débito", kind="debit", opening_balance=1000.0)
    savings1 = Account(household_id=h1.id, name="Ahorro", kind="savings", opening_balance=0)
    personal1 = Account(household_id=h1.id, name="Personal", kind="cash", opening_balance=0, owner_id=u1.id)
    account2 = Account(household_id=h2.id, name="Débito", kind="debit", opening_balance=0)
    expense1 = Category(
        household_id=h1.id, name="Comida", icon="pizza", color="#30b0c7", type="expense"
    )
    income1 = Category(
        household_id=h1.id, name="Salario", icon="briefcase", color="#00ff00", type="income"
    )
    expense2 = Category(
        household_id=h2.id, name="Comida", icon="pizza", color="#30b0c7", type="expense"
    )
    session.add_all([account1, savings1, personal1, account2, expense1, income1, expense2])
    session.commit()
    return {
        "h1": h1,
        "h2": h2,
        "u1": u1,
        "u2": u2,
        "account1": account1,
        "savings1": savings1,
        "personal1": personal1,
        "account2": account2,
        "expense1": expense1,
        "income1": income1,
        "expense2": expense2,
        "headers1": make_headers(u1),
        "headers2": make_headers(u2),
    }


def _add_transaction(session, *, household, account, category, member, tx_type, amount, tx_date, note=None):
    tx = Transaction(
        household_id=household.id,
        type=tx_type,
        amount=amount,
        category_id=category.id,
        account_id=account.id,
        member_id=member.id,
        date=tx_date,
        note=note,
    )
    session.add(tx)
    return tx


def _add_rule(session, *, household, account, category, member, rule_type, amount, frequency, next_run_date, active=True, note=None, anchor_day=None):
    rule = RecurringRule(
        household_id=household.id,
        type=rule_type,
        amount=amount,
        category_id=category.id,
        account_id=account.id,
        created_by_id=member.id,
        frequency=frequency,
        next_run_date=next_run_date,
        anchor_day=anchor_day,
        note=note,
        active=active,
    )
    session.add(rule)
    return rule


def _by_date(body: dict) -> dict[str, dict]:
    return {row["date"]: row for row in body["balance"]}


def _iso(offset_days: int) -> str:
    return (date.today() + timedelta(days=offset_days)).isoformat()


# ---------- Opening balance and series ----------


def test_opening_balance_matches_shared_accounts(client, session, world):
    """The opening balance matches the sum of shared balances from /accounts."""
    today = date.today()
    _add_transaction(
        session, household=world["h1"], account=world["account1"], category=world["income1"],
        member=world["u1"], tx_type="income", amount=500.0, tx_date=today - timedelta(days=5),
    )
    _add_transaction(
        session, household=world["h1"], account=world["account1"], category=world["expense1"],
        member=world["u1"], tx_type="expense", amount=200.0, tx_date=today - timedelta(days=3),
    )
    session.commit()

    forecast = client.get("/forecast", headers=world["headers1"])
    assert forecast.status_code == 200, forecast.text

    accounts = client.get("/accounts", headers=world["headers1"]).json()
    shared_total = round(
        sum(account["balance"] for account in accounts if not account["isPersonal"]), 2
    )
    assert forecast.json()["openingBalance"] == shared_total == 1300.0


def test_recorded_future_movements_are_baked_into_opening_once(client, session, world):
    """A movement recorded in the future is already in the opening balance
    (the formula is not filtered by date, like /accounts): it must not be
    repeated as a delta in the series, only appear in upcoming. The series
    closes: final == opening + sum."""
    _add_transaction(
        session, household=world["h1"], account=world["account1"], category=world["expense1"],
        member=world["u1"], tx_type="expense", amount=150.75, tx_date=date.today() + timedelta(days=2),
    )
    _add_transaction(
        session, household=world["h1"], account=world["account1"], category=world["income1"],
        member=world["u1"], tx_type="income", amount=1000.0, tx_date=date.today() + timedelta(days=6),
    )
    session.commit()

    resp = client.get("/forecast?days=30", headers=world["headers1"])
    assert resp.status_code == 200, resp.text
    body = resp.json()
    rows = _by_date(body)

    assert body["asOf"] == _iso(0)
    assert body["days"] == 30
    assert len(body["balance"]) == 31
    assert rows[_iso(0)]["delta"] == 0.0
    assert rows[_iso(0)]["balance"] == body["openingBalance"]

    # Already counted in the opening balance: no dip in the series.
    assert body["openingBalance"] == round(1000.0 - 150.75 + 1000.0, 2)
    for offset in (1, 2, 4, 6, 9):
        assert rows[_iso(offset)]["delta"] == 0.0
        assert rows[_iso(offset)]["income"] == 0.0
        assert rows[_iso(offset)]["expense"] == 0.0

    # The opening balance matches what /accounts shows at the same instant.
    accounts = client.get("/accounts", headers=world["headers1"]).json()
    shared_total = round(
        sum(account["balance"] for account in accounts if not account["isPersonal"]), 2
    )
    assert body["openingBalance"] == shared_total

    # But they do appear in the upcoming-movements list.
    labels = {event["date"]: event["label"] for event in body["upcoming"]}
    assert labels[_iso(2)] == "Comida"
    assert labels[_iso(6)] == "Salario"

    opening = body["openingBalance"]
    total_delta = sum(row["delta"] for row in body["balance"])
    assert body["balance"][-1]["balance"] == round(opening + total_delta, 2)


def test_default_days_returns_91_rows_and_range_validation(client, world):
    default = client.get("/forecast", headers=world["headers1"])
    assert default.status_code == 200
    body = default.json()
    assert body["days"] == 90
    assert len(body["balance"]) == 91
    assert body["balance"][0]["date"] == _iso(0)
    assert body["balance"][-1]["date"] == _iso(90)

    assert client.get("/forecast?days=13", headers=world["headers1"]).status_code == 422
    assert client.get("/forecast?days=181", headers=world["headers1"]).status_code == 422
    assert client.get("/forecast?days=14", headers=world["headers1"]).status_code == 200
    assert client.get("/forecast?days=180", headers=world["headers1"]).status_code == 200


# ---------- Recurring rules ----------


def test_weekly_rule_every_7_days_up_to_horizon(client, session, world):
    _add_rule(
        session, household=world["h1"], account=world["account1"], category=world["expense1"],
        member=world["u1"], rule_type="expense", amount=10.0, frequency="weekly",
        next_run_date=date.today() + timedelta(days=2), note="Suscripción",
    )
    session.commit()

    resp30 = client.get("/forecast?days=30", headers=world["headers1"])
    assert resp30.status_code == 200
    rows30 = _by_date(resp30.json())
    hit = [offset for offset in range(1, 31) if rows30[_iso(offset)]["delta"] != 0.0]
    assert hit == [2, 9, 16, 23, 30]
    assert all(rows30[_iso(offset)]["expense"] == 10.0 for offset in hit)

    resp90 = client.get("/forecast?days=90", headers=world["headers1"])
    rows90 = _by_date(resp90.json())
    hits90 = [offset for offset in range(1, 91) if rows90[_iso(offset)]["delta"] != 0.0]
    # 2 + 7k <= 90 => k = 0..12.
    assert hits90 == [2 + 7 * k for k in range(13)]


@pytest.mark.parametrize(("year", "february_day"), [(2027, 28), (2028, 29)])
def test_monthly_anchor_day_31_crosses_february(session, world, year, february_day):
    """Jan 31 -> Feb 28/29 -> Mar 31: the clamp comes from advance(), not the forecast."""
    _add_rule(
        session, household=world["h1"], account=world["account1"], category=world["expense1"],
        member=world["u1"], rule_type="expense", amount=2500.0, frequency="monthly",
        next_run_date=date(year, 1, 31), anchor_day=31, note="Renta",
    )
    session.commit()

    result = build_forecast(session, world["h1"].id, date(year, 1, 15), 80)
    hit_dates = [point.date for point in result.points if point.delta != 0.0]
    assert hit_dates == [date(year, 1, 31), date(year, 2, february_day), date(year, 3, 31)]
    assert all(point.balance == 1000.0 - 2500.0 * (i + 1) for i, point in enumerate(
        [p for p in result.points if p.delta != 0.0]
    ))


def test_paused_rule_projects_nothing(client, session, world):
    _add_rule(
        session, household=world["h1"], account=world["account1"], category=world["expense1"],
        member=world["u1"], rule_type="expense", amount=999.0, frequency="weekly",
        next_run_date=date.today() + timedelta(days=3), active=False,
    )
    session.commit()

    resp = client.get("/forecast?days=30", headers=world["headers1"])
    assert resp.status_code == 200
    body = resp.json()
    assert _by_date(body)[_iso(3)]["delta"] == 0.0
    assert all(event["source"] != "recurring" for event in body["upcoming"])


# ---------- Transfers and exclusions ----------


def test_transfer_shared_to_shared_moves_no_cash(client, session, world):
    resp = client.post(
        "/transactions",
        json={
            "type": "transfer",
            "amount": 300.0,
            "sourceAccountId": world["account1"].id,
            "destinationAccountId": world["savings1"].id,
            "date": _iso(5),
        },
        headers=world["headers1"],
    )
    assert resp.status_code == 201, resp.text

    forecast = client.get("/forecast?days=30", headers=world["headers1"])
    assert forecast.status_code == 200
    body = forecast.json()
    for row in body["balance"]:
        assert row["delta"] == 0.0
        assert row["income"] == 0.0
        assert row["expense"] == 0.0
    assert body["balance"][-1]["balance"] == body["openingBalance"]


def test_transfer_shared_to_personal_reduces_household_cash(client, session, world):
    """Moving cash to a personal account reduces the shared cash: already in
    the opening balance (same formula as /accounts) and with no double dip
    in the series."""
    resp = client.post(
        "/transactions",
        json={
            "type": "transfer",
            "amount": 250.0,
            "sourceAccountId": world["account1"].id,
            "destinationAccountId": world["personal1"].id,
            "date": _iso(5),
            "note": "Retiro",
        },
        headers=world["headers1"],
    )
    assert resp.status_code == 201, resp.text

    forecast = client.get("/forecast?days=30", headers=world["headers1"])
    body = forecast.json()
    rows = _by_date(body)
    accounts = client.get("/accounts", headers=world["headers1"]).json()
    shared_total = round(
        sum(account["balance"] for account in accounts if not account["isPersonal"]), 2
    )
    # The future withdrawal already reduces the opening balance (matches /accounts).
    assert body["openingBalance"] == shared_total == 750.0
    assert rows[_iso(5)]["delta"] == 0.0
    # Transfers stay excluded from the income/expense columns.
    assert rows[_iso(5)]["income"] == 0.0
    assert rows[_iso(5)]["expense"] == 0.0
    assert body["balance"][-1]["balance"] == body["openingBalance"]


def test_personal_account_and_soft_deleted_transactions_excluded(client, session, world):
    _add_transaction(
        session, household=world["h1"], account=world["personal1"], category=world["income1"],
        member=world["u1"], tx_type="income", amount=400.0, tx_date=date.today() + timedelta(days=3),
    )
    deleted = _add_transaction(
        session, household=world["h1"], account=world["account1"], category=world["expense1"],
        member=world["u1"], tx_type="expense", amount=100.0, tx_date=date.today() + timedelta(days=4),
    )
    deleted.deleted_at = datetime.now(timezone.utc)
    session.commit()

    forecast = client.get("/forecast?days=30", headers=world["headers1"])
    rows = _by_date(forecast.json())
    assert rows[_iso(3)]["delta"] == 0.0
    assert rows[_iso(4)]["delta"] == 0.0


# ---------- Read-only ----------


def test_forecast_is_read_only(client, session, world):
    _add_rule(
        session, household=world["h1"], account=world["account1"], category=world["income1"],
        member=world["u1"], rule_type="income", amount=1500.0, frequency="monthly",
        next_run_date=date.today() + timedelta(days=10), anchor_day=10,
    )
    _add_transaction(
        session, household=world["h1"], account=world["account1"], category=world["expense1"],
        member=world["u1"], tx_type="expense", amount=80.0, tx_date=date.today() + timedelta(days=5),
    )
    session.commit()

    before_count = session.scalar(
        select(func.count()).select_from(Transaction).where(Transaction.household_id == world["h1"].id)
    )
    before_runs = dict(
        session.execute(
            select(RecurringRule.id, RecurringRule.next_run_date)
            .where(RecurringRule.household_id == world["h1"].id)
        ).all()
    )

    resp = client.get("/forecast", headers=world["headers1"])
    assert resp.status_code == 200
    # The GET materializes nothing and advances no rule: no occurrence is due.
    assert before_count == session.scalar(
        select(func.count()).select_from(Transaction).where(Transaction.household_id == world["h1"].id)
    )
    after_runs = dict(
        session.execute(
            select(RecurringRule.id, RecurringRule.next_run_date)
            .where(RecurringRule.household_id == world["h1"].id)
        ).all()
    )
    assert before_runs == after_runs


# ---------- Isolation and 400 ----------


def test_forecast_is_isolated_per_household(client, session, world):
    _add_transaction(
        session, household=world["h1"], account=world["account1"], category=world["expense1"],
        member=world["u1"], tx_type="expense", amount=500.0, tx_date=date.today() + timedelta(days=2),
    )
    _add_rule(
        session, household=world["h1"], account=world["account1"], category=world["expense1"],
        member=world["u1"], rule_type="expense", amount=75.0, frequency="weekly",
        next_run_date=date.today() + timedelta(days=3),
    )
    session.commit()

    resp = client.get("/forecast?days=30", headers=world["headers2"])
    assert resp.status_code == 200
    body = resp.json()
    assert body["openingBalance"] == 0.0
    assert all(row["delta"] == 0.0 for row in body["balance"])
    assert body["upcoming"] == []


def test_user_without_household_gets_400(client, session):
    stray = User(email="sinhogar@example.com", hashed_password="x", name="Sin hogar")
    session.add(stray)
    session.commit()
    resp = client.get("/forecast", headers=make_headers(stray))
    assert resp.status_code == 400


# ---------- Upcoming movements ----------


def test_upcoming_includes_recorded_and_recurring_in_30_days(client, session, world):
    _add_transaction(
        session, household=world["h1"], account=world["account1"], category=world["expense1"],
        member=world["u1"], tx_type="expense", amount=120.0, tx_date=date.today() + timedelta(days=3),
        note="Mercado",
    )
    _add_transaction(
        session, household=world["h1"], account=world["account1"], category=world["income1"],
        member=world["u1"], tx_type="income", amount=800.0, tx_date=date.today() + timedelta(days=28),
    )
    _add_rule(
        session, household=world["h1"], account=world["account1"], category=world["expense1"],
        member=world["u1"], rule_type="expense", amount=49.0, frequency="weekly",
        next_run_date=date.today() + timedelta(days=5), note="Streaming",
    )
    # Outside the 30-day window: must not appear.
    _add_transaction(
        session, household=world["h1"], account=world["account1"], category=world["expense1"],
        member=world["u1"], tx_type="expense", amount=60.0, tx_date=date.today() + timedelta(days=32),
        note="Lejos",
    )
    session.commit()

    resp = client.get("/forecast?days=90", headers=world["headers1"])
    assert resp.status_code == 200
    upcoming = resp.json()["upcoming"]
    # The weekly rule projects all of its occurrences inside the window.
    assert [(event["date"], event["type"], event["label"], event["source"]) for event in upcoming] == [
        (_iso(3), "expense", "Mercado", "transaction"),
        (_iso(5), "expense", "Streaming", "recurring"),
        (_iso(12), "expense", "Streaming", "recurring"),
        (_iso(19), "expense", "Streaming", "recurring"),
        (_iso(26), "expense", "Streaming", "recurring"),
        # No note: label = category name.
        (_iso(28), "income", "Salario", "transaction"),
    ]
    assert all(event["amount"] in (120.0, 49.0, 800.0) for event in upcoming)
    dates = [event["date"] for event in upcoming]
    assert dates == sorted(dates)
    labels = [event["label"] for event in upcoming]
    # Outside the 30-day window: does not appear.
    assert _iso(32) not in dates
    assert "Lejos" not in labels


def test_upcoming_is_capped_at_20(client, session, world):
    for offset in range(1, 22):
        _add_transaction(
            session, household=world["h1"], account=world["account1"], category=world["expense1"],
            member=world["u1"], tx_type="expense", amount=10.0,
            tx_date=date.today() + timedelta(days=offset), note=f"m{offset}",
        )
    session.commit()

    resp = client.get("/forecast?days=60", headers=world["headers1"])
    assert resp.status_code == 200
    upcoming = resp.json()["upcoming"]
    assert len(upcoming) == 20
    labels = {event["label"] for event in upcoming}
    # With 21 candidates in the window, the ordered cut leaves the last out.
    assert "m21" not in labels


def test_upcoming_includes_transfer_to_personal(client, session, world):
    resp = client.post(
        "/transactions",
        json={
            "type": "transfer",
            "amount": 100.0,
            "sourceAccountId": world["account1"].id,
            "destinationAccountId": world["personal1"].id,
            "date": _iso(7),
            "note": "Giro",
        },
        headers=world["headers1"],
    )
    assert resp.status_code == 201

    upcoming = client.get("/forecast?days=30", headers=world["headers1"]).json()["upcoming"]
    transfer_events = [event for event in upcoming if event["label"] == "Giro"]
    assert transfer_events == [
        {"date": _iso(7), "type": "expense", "amount": 100.0, "label": "Giro", "source": "transaction"}
    ]


# ---------- Card due and instalment due (advisory liquidity events) ----------


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


@pytest.fixture(name="card_world")
def card_world_fixture(session):
    user = User(email="card@example.com", hashed_password="x", name="Card")
    session.add(user)
    session.flush()
    household = Household(name="Tarjetas", owner_id=user.id)
    session.add(household)
    session.flush()
    user.household_id = household.id
    category = Category(household_id=household.id, name="Hogar", icon="x", color="#000000", type="expense")
    card, cash = (
        Account(household_id=household.id, name="BBVA", kind="credit", opening_balance=0),
        Account(household_id=household.id, name="Efectivo", kind="cash", opening_balance=20000),
    )
    session.add_all([category, card, cash])
    session.commit()
    return {
        "user": user,
        "household": household,
        "category": category,
        "card": card,
        "cash": cash,
        "headers": make_headers(user),
    }


def test_card_due_event_in_upcoming(client, session, card_world):
    today = date.today()
    statement_day, due_days = _cycle_for_due(10)
    card_world["card"].statement_day = statement_day
    card_world["card"].payment_due_days = due_days
    session.add(
        Transaction(
            household_id=card_world["household"].id, type="expense", amount=12000,
            category_id=card_world["category"].id, account_id=card_world["card"].id,
            member_id=card_world["user"].id, date=today,
        )
    )
    session.commit()

    upcoming = client.get("/forecast?days=30", headers=card_world["headers"]).json()["upcoming"]
    card_events = [event for event in upcoming if event["source"] == "card_due"]
    assert len(card_events) == 1
    event = card_events[0]
    assert event["type"] == "expense"
    assert event["amount"] == 12000.0
    assert "BBVA" in event["label"]
    # the advisory event must not move the balance series
    body = client.get("/forecast?days=30", headers=card_world["headers"]).json()
    rows = _by_date(body)
    assert rows[_iso(0)]["balance"] == body["openingBalance"]
    assert rows[_iso(30)]["balance"] == round(body["openingBalance"] + sum(row["delta"] for row in body["balance"]), 2)


def test_card_due_reduced_by_scheduled_inflows(client, session, card_world):
    statement_day, due_days = _cycle_for_due(10)
    card_world["card"].statement_day = statement_day
    card_world["card"].payment_due_days = due_days
    session.add(
        Transaction(
            household_id=card_world["household"].id, type="expense", amount=12000,
            category_id=card_world["category"].id, account_id=card_world["card"].id,
            member_id=card_world["user"].id, date=date.today(),
        )
    )
    session.commit()
    resp = client.post(
        "/transactions",
        json={
            "type": "transfer",
            "amount": 5000.0,
            "sourceAccountId": card_world["cash"].id,
            "destinationAccountId": card_world["card"].id,
            "date": _iso(2),
        },
        headers=card_world["headers"],
    )
    assert resp.status_code == 201, resp.text
    upcoming = client.get("/forecast?days=30", headers=card_world["headers"]).json()["upcoming"]
    card_events = [event for event in upcoming if event["source"] == "card_due"]
    assert len(card_events) == 1
    assert card_events[0]["amount"] == 7000.0


def test_no_card_due_without_cycle(client, session, card_world):
    session.add(
        Transaction(
            household_id=card_world["household"].id, type="expense", amount=12000,
            category_id=card_world["category"].id, account_id=card_world["card"].id,
            member_id=card_world["user"].id, date=date.today(),
        )
    )
    session.commit()
    upcoming = client.get("/forecast?days=30", headers=card_world["headers"]).json()["upcoming"]
    assert [event for event in upcoming if event["source"] == "card_due"] == []


def test_instalment_due_events_only_for_active_plans(client, session, card_world):
    from app.models import InstalmentPlan

    today = date.today()
    session.add(
        Transaction(
            household_id=card_world["household"].id, type="expense", amount=3000,
            category_id=card_world["category"].id, account_id=card_world["card"].id,
            member_id=card_world["user"].id, date=today,
        )
    )
    session.commit()
    purchase = session.query(Transaction).filter_by(amount=3000).one()
    purchase2 = Transaction(
        household_id=card_world["household"].id, type="expense", amount=1200,
        category_id=card_world["category"].id, account_id=card_world["card"].id,
        member_id=card_world["user"].id, date=today,
    )
    session.add_all([purchase2])
    session.flush()
    active_plan = InstalmentPlan(
        household_id=card_world["household"].id,
        account_id=card_world["card"].id,
        source_transaction_id=purchase.id,
        months=3,
        total_amount=3000,
        monthly_amount=1000,
        first_due_date=today + timedelta(days=5),
        created_by_id=card_world["user"].id,
    )
    paused = InstalmentPlan(
        household_id=card_world["household"].id,
        account_id=card_world["card"].id,
        source_transaction_id=purchase2.id,
        months=3,
        total_amount=1200,
        monthly_amount=400,
        first_due_date=today + timedelta(days=5),
        created_by_id=card_world["user"].id,
        status="paused",
    )
    session.add_all([active_plan, paused])
    session.commit()

    upcoming = client.get("/forecast?days=30", headers=card_world["headers"]).json()["upcoming"]
    instalment_events = [event for event in upcoming if event["source"] == "instalment_due"]
    assert len(instalment_events) == 1  # the paused plan is not listed
    assert instalment_events[0]["amount"] == 1000.0
    assert instalment_events[0]["date"] == _iso(5)
