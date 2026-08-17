from datetime import date, datetime, timedelta, timezone

import jwt
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Account, Category, Household, Transaction, User


def _headers(user: User) -> dict[str, str]:
    token = jwt.encode(
        {"sub": user.id, "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    return {"Authorization": f"Bearer {token}"}


def _setup(session: Session, card_personal=False) -> tuple[dict[str, str], str, str, str]:
    """Household + user + shared card + cash + an expense on the card."""
    user = User(email="owner@example.com", hashed_password="x", name="Owner")
    session.add(user)
    session.flush()
    household = Household(name="Casa", owner_id=user.id)
    session.add(household)
    session.flush()
    user.household_id = household.id
    category = Category(household_id=household.id, name="Hogar", icon="x", color="#000000", type="expense")
    card = Account(household_id=household.id, name="BBVA", kind="credit", opening_balance=0)
    cash = Account(household_id=household.id, name="Efectivo", kind="cash", opening_balance=5000)
    if card_personal:
        card.owner_id = user.id
    session.add_all([category, card, cash])
    session.flush()
    session.add(
        Transaction(
            household_id=household.id, type="expense", amount=5100,
            category_id=category.id, account_id=card.id, member_id=user.id,
            date=date(2026, 8, 10),
        )
    )
    session.commit()
    purchase = session.query(Transaction).one()
    return _headers(user), card.id, cash.id, purchase.id


def _future(days: int) -> str:
    return (date.today() + timedelta(days=days)).isoformat()


def test_create_plan_from_card_purchase(client, session):
    headers, card_id, _, purchase_id = _setup(session)
    res = client.post(
        "/instalment-plans",
        json={"sourceTransactionId": purchase_id, "months": 6, "firstDueDate": _future(30)},
        headers=headers,
    )
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["months"] == 6
    assert body["totalAmount"] == 5100.0
    assert body["monthlyAmount"] == 850.0
    assert body["status"] == "active"
    assert body["paidCount"] == 0
    assert body["accountId"] == card_id
    assert body["accountName"] == "BBVA"
    assert body["nextDueDate"] == _future(30)
    assert body["nextDueAmount"] == 850.0
    assert len(body["schedule"]) == 6
    assert body["schedule"][0]["paid"] is False
    assert all(item["amount"] == 850.0 for item in body["schedule"])


def test_create_plan_rounding_remainder(client, session):
    headers, card_id, _, _ = _setup(session)
    user = session.query(User).one()
    household = session.query(Household).one()
    category = session.query(Category).one()
    session.add(
        Transaction(
            household_id=household.id, type="expense", amount=5101,
            category_id=category.id, account_id=card_id, member_id=user.id,
            date=date.today(),
        )
    )
    session.commit()
    odd_purchase = session.query(Transaction).filter_by(amount=5101).one()
    res = client.post(
        "/instalment-plans",
        json={"sourceTransactionId": odd_purchase.id, "months": 6, "firstDueDate": _future(30)},
        headers=headers,
    )
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["monthlyAmount"] == 850.1667
    amounts = [item["amount"] for item in body["schedule"]]
    assert amounts[:5] == [850.1667] * 5
    assert amounts[5] == round(5101.0 - 5 * 850.1667, 4)  # 850.1665
    assert round(sum(amounts), 4) == 5101.0


def test_create_plan_guards(client, session):
    headers, card_id, cash_id, purchase_id = _setup(session)
    create = lambda: client.post(
        "/instalment-plans",
        json={"sourceTransactionId": purchase_id, "months": 6, "firstDueDate": _future(30)},
        headers=headers,
    )
    assert create().status_code == 201
    assert create().status_code == 409  # one plan per purchase

    res = client.post(
        "/instalment-plans",
        json={"sourceTransactionId": "missing", "months": 6, "firstDueDate": _future(30)},
        headers=headers,
    )
    assert res.status_code == 404
    # months out of range
    res = client.post(
        "/instalment-plans",
        json={"sourceTransactionId": purchase_id, "months": 1, "firstDueDate": _future(30)},
        headers=headers,
    )
    assert res.status_code == 422


def test_create_plan_rejects_non_card_purchase(client, session):
    headers, _, cash_id, _ = _setup(session)
    user = session.query(User).one()
    household = session.query(Household).one()
    category = session.query(Category).one()
    session.add(
        Transaction(
            household_id=household.id, type="expense", amount=100,
            category_id=category.id, account_id=cash_id, member_id=user.id,
            date=date.today(),
        )
    )
    session.commit()
    cash_purchase = session.query(Transaction).filter_by(account_id=cash_id).one()
    res = client.post(
        "/instalment-plans",
        json={"sourceTransactionId": cash_purchase.id, "months": 3, "firstDueDate": _future(30)},
        headers=headers,
    )
    assert res.status_code == 422


def test_create_plan_rejects_personal_card(client, session):
    headers, card_id, _, purchase_id = _setup(session, card_personal=True)
    res = client.post(
        "/instalment-plans",
        json={"sourceTransactionId": purchase_id, "months": 6, "firstDueDate": _future(30)},
        headers=headers,
    )
    assert res.status_code == 422


def test_list_and_detail_and_isolation(client, session):
    headers, card_id, _, purchase_id = _setup(session)
    created = client.post(
        "/instalment-plans",
        json={"sourceTransactionId": purchase_id, "months": 6, "firstDueDate": _future(30)},
        headers=headers,
    ).json()
    listing = client.get("/instalment-plans", headers=headers).json()
    assert [plan["id"] for plan in listing] == [created["id"]]
    detail = client.get(f"/instalment-plans/{created['id']}", headers=headers).json()
    assert detail["id"] == created["id"]
    # other household: no access
    other = User(email="other@example.com", hashed_password="x", name="Other")
    session.add(other)
    session.flush()
    other_household = Household(name="Otra", owner_id=other.id)
    session.add(other_household)
    session.flush()
    other.household_id = other_household.id
    session.commit()
    other_headers = _headers(other)
    assert client.get("/instalment-plans", headers=other_headers).json() == []
    assert client.get(f"/instalment-plans/{created['id']}", headers=other_headers).status_code == 404


def test_pay_marks_instalment(client, session):
    headers, _, _, purchase_id = _setup(session)
    plan = client.post(
        "/instalment-plans",
        json={"sourceTransactionId": purchase_id, "months": 6, "firstDueDate": _future(30)},
        headers=headers,
    ).json()
    res = client.post(f"/instalment-plans/{plan['id']}/pay", json={}, headers=headers)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["paidCount"] == 1
    assert body["schedule"][0]["paid"] is True
    first = date.fromisoformat(body["schedule"][0]["date"])
    second = date.fromisoformat(body["schedule"][1]["date"])
    assert body["nextDueDate"] == second.isoformat()


def test_pay_with_transfer_moves_balances(client, session):
    headers, card_id, cash_id, purchase_id = _setup(session)
    plan = client.post(
        "/instalment-plans",
        json={"sourceTransactionId": purchase_id, "months": 6, "firstDueDate": _future(30)},
        headers=headers,
    ).json()
    res = client.post(
        f"/instalment-plans/{plan['id']}/pay",
        json={"sourceAccountId": cash_id, "date": _future(0)},
        headers=headers,
    )
    assert res.status_code == 200, res.text
    assert res.json()["paidCount"] == 1
    accounts = {row["id"]: row for row in client.get("/accounts", headers=headers).json()}
    # cash paid out 850 (5000 opening), card received 850 back (0 opening - 5100 expense + 850)
    assert accounts[cash_id]["balance"] == 5000.0 - 850.0
    assert accounts[card_id]["balance"] == -5100.0 + 850.0
    # transfers are excluded from expense totals
    summary = client.get("/summary/month", headers=headers).json()
    assert summary["expense"] == 5100.0
    transfer_rows = [
        row for row in client.get("/transactions", params={"includeTransfers": "true"}, headers=headers).json()
        if row["type"] == "transfer"
    ]
    assert len(transfer_rows) == 2
    assert all("Instalado 1/6" in (row["note"] or "") for row in transfer_rows)


def test_pay_completes_at_last_instalment(client, session):
    headers, _, _, purchase_id = _setup(session)
    plan = client.post(
        "/instalment-plans",
        json={"sourceTransactionId": purchase_id, "months": 2, "firstDueDate": _future(30)},
        headers=headers,
    ).json()
    for _ in range(2):
        res = client.post(f"/instalment-plans/{plan['id']}/pay", json={}, headers=headers)
        assert res.status_code == 200
    body = res.json()
    assert body["status"] == "completed"
    assert body["nextDueDate"] is None
    assert client.post(f"/instalment-plans/{plan['id']}/pay", json={}, headers=headers).status_code == 409


def test_pause_resume_cancel(client, session):
    headers, _, _, purchase_id = _setup(session)
    plan = client.post(
        "/instalment-plans",
        json={"sourceTransactionId": purchase_id, "months": 6, "firstDueDate": _future(30)},
        headers=headers,
    ).json()
    url = f"/instalment-plans/{plan['id']}"
    assert client.post(f"{url}/pause", headers=headers).json()["status"] == "paused"
    assert client.post(f"{url}/pay", json={}, headers=headers).status_code == 409  # paused: no pay
    assert client.post(f"{url}/resume", headers=headers).json()["status"] == "active"
    assert client.delete(url, headers=headers).status_code == 204
    assert client.get("/instalment-plans", headers=headers).json() == []  # cancelled: hidden
    detail = client.get(url, headers=headers).json()
    assert detail["status"] == "cancelled"
    assert client.post(f"{url}/pause", headers=headers).status_code == 409


def test_pause_is_listed(client, session):
    headers, _, _, purchase_id = _setup(session)
    plan = client.post(
        "/instalment-plans",
        json={"sourceTransactionId": purchase_id, "months": 6, "firstDueDate": _future(30)},
        headers=headers,
    ).json()
    client.post(f"/instalment-plans/{plan['id']}/pause", headers=headers)
    listing = client.get("/instalment-plans", headers=headers).json()
    assert [row["status"] for row in listing] == ["paused"]


def test_delete_purchase_blocked_by_active_plan(client, session):
    headers, _, _, purchase_id = _setup(session)
    plan = client.post(
        "/instalment-plans",
        json={"sourceTransactionId": purchase_id, "months": 6, "firstDueDate": _future(30)},
        headers=headers,
    ).json()
    res = client.delete(f"/transactions/{purchase_id}", headers=headers)
    assert res.status_code == 409
    assert "plan" in res.json()["detail"]
    # after cancelling the plan, the purchase can be deleted
    assert client.delete(f"/instalment-plans/{plan['id']}", headers=headers).status_code == 204
    assert client.delete(f"/transactions/{purchase_id}", headers=headers).status_code == 204


def test_edit_purchase_amount_blocked_by_active_plan(client, session):
    headers, _, _, purchase_id = _setup(session)
    plan = client.post(
        "/instalment-plans",
        json={"sourceTransactionId": purchase_id, "months": 6, "firstDueDate": _future(30)},
        headers=headers,
    ).json()
    assert client.patch(f"/transactions/{purchase_id}", json={"amount": 9999}, headers=headers).status_code == 409
    # non-amount edits are still allowed
    res = client.patch(f"/transactions/{purchase_id}", json={"note": "hola"}, headers=headers)
    assert res.status_code == 200, res.text
