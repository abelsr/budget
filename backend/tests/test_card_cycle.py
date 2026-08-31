from datetime import date

from sqlalchemy.orm import Session

from app.models import Household, User
from tests.helpers import auth_headers as _headers


def _household_with_user(session: Session) -> tuple[Household, User, dict[str, str]]:
    user = User(email="owner@example.com", hashed_password="x", name="Owner")
    session.add(user)
    session.flush()
    household = Household(name="Casa", owner_id=user.id)
    session.add(household)
    session.flush()
    user.household_id = household.id
    session.commit()
    return household, user, _headers(user)


def test_credit_account_accepts_cycle_and_derives_dates(client, session):
    household, user, headers = _household_with_user(session)
    res = client.post(
        "/accounts",
        json={"name": "BBVA", "kind": "credit", "statementDay": 15, "paymentDueDays": 20},
        headers=headers,
    )
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["statementDay"] == 15
    assert body["paymentDueDays"] == 20
    assert body["nextStatementDate"] is not None
    assert body["lastStatementDate"] is not None
    assert body["nextPaymentDueDate"] is not None
    today = date.today()
    from app.services.card_calendar import last_statement_date, next_statement_date, payment_due_date

    nxt = next_statement_date(15, today)
    assert date.fromisoformat(body["nextStatementDate"]) == nxt
    assert date.fromisoformat(body["lastStatementDate"]) == last_statement_date(15, today)
    assert date.fromisoformat(body["nextPaymentDueDate"]) == payment_due_date(nxt, 20)


def test_non_credit_account_rejects_cycle(client, session):
    _, _, headers = _household_with_user(session)
    res = client.post(
        "/accounts",
        json={"name": "Efectivo", "kind": "cash", "statementDay": 15, "paymentDueDays": 20},
        headers=headers,
    )
    assert res.status_code == 422


def test_patch_kind_to_cash_requires_clearing_cycle(client, session):
    household, user, headers = _household_with_user(session)
    created = client.post(
        "/accounts", json={"name": "BBVA", "kind": "credit", "statementDay": 15, "paymentDueDays": 20}, headers=headers
    ).json()
    assert client.patch(f"/accounts/{created['id']}", json={"kind": "cash"}, headers=headers).status_code == 422
    res = client.patch(
        f"/accounts/{created['id']}",
        json={"kind": "cash", "statementDay": None, "paymentDueDays": None},
        headers=headers,
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["statementDay"] is None
    assert body["nextStatementDate"] is None
    assert body["nextPaymentDueDate"] is None


def test_patch_cycle_requires_credit_kind(client, session):
    household, user, headers = _household_with_user(session)
    cash = client.post("/accounts", json={"name": "Efectivo", "kind": "cash"}, headers=headers).json()
    assert client.patch(f"/accounts/{cash['id']}", json={"statementDay": 15}, headers=headers).status_code == 422
    res = client.patch(
        f"/accounts/{cash['id']}",
        json={"kind": "credit", "statementDay": 15, "paymentDueDays": 20},
        headers=headers,
    )
    assert res.status_code == 200, res.text
    assert res.json()["nextPaymentDueDate"] is not None
