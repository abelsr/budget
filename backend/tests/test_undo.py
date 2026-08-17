from datetime import date, datetime, timedelta, timezone

import jwt
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Account, Category, Household, ReconciliationSession, Transaction, TransferGroup, User


def _headers(user: User) -> dict[str, str]:
    token = jwt.encode(
        {"sub": user.id, "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    return {"Authorization": f"Bearer {token}"}


def _setup(session: Session) -> tuple[dict, str, str, str]:
    """Household + user + shared cash account + an expense on it."""
    user = User(email="owner@example.com", hashed_password="x", name="Owner")
    session.add(user)
    session.flush()
    household = Household(name="Casa", owner_id=user.id)
    session.add(household)
    session.flush()
    user.household_id = household.id
    category = Category(household_id=household.id, name="Comida", icon="x", color="#000000", type="expense")
    account = Account(household_id=household.id, name="Efectivo", kind="cash", opening_balance=1000)
    session.add_all([category, account])
    session.flush()
    session.add(
        Transaction(
            household_id=household.id, type="expense", amount=100,
            category_id=category.id, account_id=account.id,
            member_id=user.id, date=date.today(),
        )
    )
    session.commit()
    tx = session.query(Transaction).one()
    return _headers(user), account.id, tx.id, household.id


def test_delete_is_soft_delete(client, session):
    headers, _, tx_id, _ = _setup(session)
    assert client.delete(f"/transactions/{tx_id}", headers=headers).status_code == 204
    # hidden everywhere
    assert [row["id"] for row in client.get("/transactions", headers=headers).json()] == []
    assert client.get("/summary/month", headers=headers).json()["expense"] == 0.0
    # but the row still exists, soft-deleted with reason manual
    row = session.get(Transaction, tx_id)
    assert row.deleted_at is not None
    assert row.delete_reason == "manual"
    # account balance reflects the deletion
    accounts = client.get("/accounts", headers=headers).json()
    assert accounts[0]["balance"] == 1000.0


def test_delete_transfer_soft_deletes_both_rows_and_keeps_group(client, session):
    headers, account_id, _, household_id = _setup(session)
    session.add(Account(household_id=household_id, name="Débito", kind="debit", opening_balance=0))
    session.commit()
    debit_id = session.query(Account).filter_by(name="Débito").one().id
    res = client.post(
        "/transactions",
        json={
            "type": "transfer", "amount": 50, "sourceAccountId": account_id,
            "destinationAccountId": debit_id, "date": date.today().isoformat(),
        },
        headers=headers,
    )
    assert res.status_code == 201, res.text
    assert client.delete(f"/transactions/{res.json()['id']}", headers=headers).status_code == 204
    group_id = res.json()["transferGroupId"]
    rows = session.query(Transaction).filter_by(transfer_group_id=group_id).all()
    assert len(rows) == 2
    assert all(row.deleted_at is not None and row.delete_reason == "manual" for row in rows)
    # the group is kept on purpose: its client_id must keep blocking replays
    assert session.get(TransferGroup, group_id) is not None
    balances = {row["id"]: row["balance"] for row in client.get("/accounts", headers=headers).json()}
    assert balances[account_id] == 900.0  # 1000 opening - 100 expense
    assert balances[debit_id] == 0.0


def test_restore_one_off(client, session):
    headers, _, tx_id, _ = _setup(session)
    client.delete(f"/transactions/{tx_id}", headers=headers)
    res = client.post(f"/transactions/{tx_id}/restore", headers=headers)
    assert res.status_code == 200, res.text
    assert res.json()["id"] == tx_id
    assert [row["id"] for row in client.get("/transactions", headers=headers).json()] == [tx_id]
    assert client.get("/summary/month", headers=headers).json()["expense"] == 100.0
    row = session.get(Transaction, tx_id)
    assert row.deleted_at is None
    assert row.delete_reason is None


def test_restore_transfer_restores_both_rows(client, session):
    headers, account_id, _, household_id = _setup(session)
    session.add(Account(household_id=household_id, name="Débito", kind="debit", opening_balance=0))
    session.commit()
    debit_id = session.query(Account).filter_by(name="Débito").one().id
    res = client.post(
        "/transactions",
        json={
            "type": "transfer", "amount": 50, "sourceAccountId": account_id,
            "destinationAccountId": debit_id, "date": date.today().isoformat(),
        },
        headers=headers,
    )
    assert res.status_code == 201, res.text
    transfer_id = res.json()["id"]
    client.delete(f"/transactions/{transfer_id}", headers=headers)
    res = client.post(f"/transactions/{transfer_id}/restore", headers=headers)
    assert res.status_code == 200, res.text
    rows = session.query(Transaction).filter_by(transfer_group_id=res.json()["transferGroupId"]).all()
    assert len(rows) == 2
    assert all(row.deleted_at is None and row.delete_reason is None for row in rows)
    balances = {row["id"]: row["balance"] for row in client.get("/accounts", headers=headers).json()}
    assert balances[account_id] == 850.0  # 1000 opening - 100 expense - 50 transfer
    assert balances[debit_id] == 50.0


def test_restore_guards(client, session):
    headers, _, tx_id, _ = _setup(session)
    # not deleted -> 404
    assert client.post(f"/transactions/{tx_id}/restore", headers=headers).status_code == 404
    # import-reverted row -> 409 (simulate by setting the flags directly)
    client.delete(f"/transactions/{tx_id}", headers=headers)
    row = session.get(Transaction, tx_id)
    row.delete_reason = "import_revert"
    session.commit()
    assert client.post(f"/transactions/{tx_id}/restore", headers=headers).status_code == 409
    # other household -> 404
    other = User(email="other@example.com", hashed_password="x", name="Other")
    session.add(other)
    session.flush()
    other_household = Household(name="Otra", owner_id=other.id)
    session.add(other_household)
    session.flush()
    other.household_id = other_household.id
    session.commit()
    assert client.post(f"/transactions/{tx_id}/restore", headers=_headers(other)).status_code == 404


def test_client_id_replay_after_soft_delete_still_409(client, session):
    headers, account_id, _, _ = _setup(session)
    category_id = session.query(Category).one().id
    payload = {
        "type": "expense", "amount": 10, "categoryId": category_id,
        "accountId": account_id, "date": date.today().isoformat(), "clientId": "123e4567-e89b-12d3-a456-426614174000",
    }
    res = client.post("/transactions", json=payload, headers=headers)
    assert res.status_code == 201, res.text
    client.delete(f"/transactions/{res.json()['id']}", headers=headers)
    replay = client.post("/transactions", json=payload, headers=headers)
    assert replay.status_code == 409


def test_restore_invalidates_completed_reconciliation(client, session):
    headers, account_id, tx_id, household_id = _setup(session)
    tx = session.get(Transaction, tx_id)
    session.add(
        ReconciliationSession(
            account_id=account_id, household_id=household_id,
            statement_date=date.today(), statement_balance=900,
            status="completed", created_by_id=tx.member_id,
            completed_at=datetime.now(timezone.utc),
        )
    )
    session.flush()
    session_id = session.query(ReconciliationSession).one().id
    tx.reconciliation_session_id = session_id
    session.commit()
    # the deleted tx made the session stale
    client.delete(f"/transactions/{tx_id}", headers=headers)
    assert session.get(ReconciliationSession, session_id).status == "stale"
    # restoring keeps it stale (it must be reviewed again, not auto-completed)
    client.post(f"/transactions/{tx_id}/restore", headers=headers)
    assert session.get(ReconciliationSession, session_id).status == "stale"
