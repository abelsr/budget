import pytest
from datetime import date, datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models import (
    Account,
    Attachment,
    Category,
    Household,
    InstalmentPlan,
    Transaction,
    TransactionEditEvent,
    TransactionSplit,
    TransferGroup,
    User,
)
from app.services import housekeeping
from tests.helpers import auth_headers as _headers


@pytest.fixture(autouse=True)
def _reset_purge_guard():
    housekeeping.reset_purge_guard()
    yield
    housekeeping.reset_purge_guard()


def _setup(session: Session) -> tuple[dict, str, str, str, str]:
    """Household + user + cash account; returns (headers, account_id, category_id, household_id, user_id)."""
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
    session.commit()
    return _headers(user), account.id, category.id, household.id, user.id


def _expense(session: Session, household_id: str, account_id: str, category_id: str, member_id: str, amount=100) -> str:
    tx = Transaction(
        household_id=household_id, type="expense", amount=amount,
        category_id=category_id, account_id=account_id, member_id=member_id, date=date.today(),
    )
    session.add(tx)
    session.flush()
    return tx.id


def _age(session: Session, tx_id: str, days: int) -> None:
    tx = session.get(Transaction, tx_id)
    tx.deleted_at = datetime.now(timezone.utc) - timedelta(days=days)
    tx.delete_reason = "manual"
    session.commit()


def test_purge_removes_rows_older_than_retention(client, session):
    headers, account_id, category_id, household_id, user_id = _setup(session)
    old_id = _expense(session, household_id, account_id, category_id, user_id)
    fresh_id = _expense(session, household_id, account_id, category_id, user_id, amount=50)
    _age(session, old_id, housekeeping.RETENTION_DAYS + 1)
    _age(session, fresh_id, housekeeping.RETENTION_DAYS - 1)
    # a read triggers the materialize_due pass, which runs the once-per-day purge
    assert client.get("/transactions", headers=headers).status_code == 200
    assert session.get(Transaction, old_id) is None
    fresh = session.get(Transaction, fresh_id)
    assert fresh is not None and fresh.deleted_at is not None  # kept, still soft-deleted


def test_purge_removes_dependents(client, session, monkeypatch):
    headers, account_id, category_id, household_id, user_id = _setup(session)
    tx_id = _expense(session, household_id, account_id, category_id, user_id)
    session.add(TransactionSplit(transaction_id=tx_id, category_id=category_id, amount=100))
    session.add(
        TransactionEditEvent(
            transaction_id=tx_id, edited_by_id=user_id,
            before_snapshot={"amount": 50}, after_snapshot={"amount": 100},
        )
    )
    session.add(
        Attachment(
            transaction_id=tx_id, household_id=household_id, filename="recibo.jpg",
            content_type="image/jpeg", size_bytes=12,
            storage_path="attachments/household/recibo.jpg",
        )
    )
    session.commit()
    _age(session, tx_id, housekeeping.RETENTION_DAYS + 1)
    deleted: list[str] = []
    monkeypatch.setattr(housekeeping, "delete_attachment", deleted.append)
    assert client.get("/transactions", headers=headers).status_code == 200
    assert session.get(Transaction, tx_id) is None
    assert session.query(TransactionSplit).count() == 0
    assert session.query(TransactionEditEvent).count() == 0
    assert session.query(Attachment).count() == 0
    assert deleted == ["attachments/household/recibo.jpg"]


def test_purge_removes_transfer_group_once_both_rows_gone(client, session):
    headers, account_id, category_id, household_id, user_id = _setup(session)
    session.add(Account(household_id=household_id, name="Débito", kind="debit", opening_balance=0))
    session.commit()
    debit_id = session.query(Account).filter_by(name="Débito").one().id
    old_group, fresh_group = None, None
    for age_days in (housekeeping.RETENTION_DAYS + 1, housekeeping.RETENTION_DAYS - 1):
        res = client.post(
            "/transactions",
            json={"type": "transfer", "amount": 20, "sourceAccountId": account_id,
                  "destinationAccountId": debit_id, "date": date.today().isoformat()},
            headers=headers,
        )
        assert res.status_code == 201, res.text
        group_id = res.json()["transferGroupId"]
        if age_days > housekeeping.RETENTION_DAYS:
            old_group = group_id
        else:
            fresh_group = group_id
        for row in session.query(Transaction).filter_by(transfer_group_id=group_id).all():
            row.deleted_at = datetime.now(timezone.utc) - timedelta(days=age_days)
            row.delete_reason = "manual"
        session.commit()
    assert client.get("/transactions", headers=headers).status_code == 200
    assert session.get(TransferGroup, old_group) is None
    assert session.get(TransferGroup, fresh_group) is not None


def test_purge_skips_rows_referenced_by_instalment_plans(client, session):
    headers, account_id, category_id, household_id, user_id = _setup(session)
    tx_id = _expense(session, household_id, account_id, category_id, user_id)
    session.add(
        InstalmentPlan(
            household_id=household_id, account_id=account_id,
            source_transaction_id=tx_id, months=12,
            total_amount=1200, monthly_amount=100,
            first_due_date=date.today().replace(day=1),
            created_by_id=user_id,
        )
    )
    session.commit()
    _age(session, tx_id, housekeeping.RETENTION_DAYS + 1)
    assert client.get("/transactions", headers=headers).status_code == 200
    assert session.get(Transaction, tx_id) is not None  # FK target of the plan; kept


def test_purge_runs_at_most_once_per_day(client, session):
    headers, account_id, category_id, household_id, user_id = _setup(session)
    first_id = _expense(session, household_id, account_id, category_id, user_id)
    _age(session, first_id, housekeeping.RETENTION_DAYS + 1)
    assert client.get("/transactions", headers=headers).status_code == 200
    assert session.get(Transaction, first_id) is None
    # a second aged row appearing the same day is NOT purged until the next day
    second_id = _expense(session, household_id, account_id, category_id, user_id, amount=60)
    _age(session, second_id, housekeeping.RETENTION_DAYS + 1)
    assert client.get("/transactions", headers=headers).status_code == 200
    assert session.get(Transaction, second_id) is not None


def test_purge_failure_never_breaks_reads(client, session, monkeypatch):
    headers, account_id, category_id, household_id, user_id = _setup(session)
    tx_id = _expense(session, household_id, account_id, category_id, user_id)
    _age(session, tx_id, housekeeping.RETENTION_DAYS + 1)
    monkeypatch.setattr(housekeeping, "_purge_one", lambda db, tx: (_ for _ in ()).throw(RuntimeError("minio down")))
    assert client.get("/transactions", headers=headers).status_code == 200
    assert client.get("/summary/month", headers=headers).status_code == 200
