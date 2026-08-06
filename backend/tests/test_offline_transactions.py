import pytest
from sqlalchemy.exc import IntegrityError

from app.models import Account, Household, Transaction, User
from tests.test_core import create_account, create_category, make_headers


@pytest.fixture(name="world")
def world_fixture(session):
    first = User(email="offline-one@example.com", hashed_password="x", name="One")
    second = User(email="offline-two@example.com", hashed_password="x", name="Two")
    session.add_all([first, second])
    session.flush()
    first_household = Household(name="First", owner_id=first.id)
    second_household = Household(name="Second", owner_id=second.id)
    session.add_all([first_household, second_household])
    session.flush()
    first.household_id = first_household.id
    second.household_id = second_household.id
    session.commit()
    return {
        "headers1": make_headers(first),
        "headers2": make_headers(second),
    }


def _payload(category_id: str, account_id: str, client_id: str) -> dict[str, object]:
    return {
        "clientId": client_id,
        "type": "expense",
        "amount": 42.5,
        "categoryId": category_id,
        "accountId": account_id,
        "date": "2026-08-05",
        "note": "Compra sin conexión",
    }


def test_client_id_replays_identical_transaction_once(client, session, world):
    account = create_account(client, world["headers1"])
    category = create_category(client, world["headers1"])
    payload = _payload(category["id"], account["id"], "6f6287ce-98c1-4f08-b506-58ff4de2d0bb")

    first = client.post("/transactions", json=payload, headers=world["headers1"])
    retry = client.post("/transactions", json=payload, headers=world["headers1"])

    assert first.status_code == retry.status_code == 201
    assert retry.json()["id"] == first.json()["id"]
    assert retry.json()["clientId"] == payload["clientId"]
    assert session.query(Transaction).count() == 1


@pytest.mark.parametrize("amount", [12.34, 0.1])
def test_client_id_replays_decimal_money_values(client, session, world, amount):
    account = create_account(client, world["headers1"])
    category = create_category(client, world["headers1"])
    payload = _payload(category["id"], account["id"], "8b7fda4e-6dca-48b5-94aa-324f080bb671")
    payload["amount"] = amount

    first = client.post("/transactions", json=payload, headers=world["headers1"])
    retry = client.post("/transactions", json=payload, headers=world["headers1"])

    assert first.status_code == retry.status_code == 201
    assert first.json()["id"] == retry.json()["id"]
    assert session.query(Transaction).count() == 1


def test_client_id_rejects_a_changed_payload(client, session, world):
    account = create_account(client, world["headers1"])
    category = create_category(client, world["headers1"])
    payload = _payload(category["id"], account["id"], "2a3b9393-2e76-4c51-b697-93431dd8b6d5")
    assert client.post("/transactions", json=payload, headers=world["headers1"]).status_code == 201

    payload["amount"] = 99
    response = client.post("/transactions", json=payload, headers=world["headers1"])

    assert response.status_code == 409
    assert response.json()["detail"] == "El clientId ya se usó con un movimiento distinto"
    assert session.query(Transaction).count() == 1


def test_client_id_is_scoped_to_the_household(client, world):
    account1 = create_account(client, world["headers1"])
    category1 = create_category(client, world["headers1"])
    account2 = create_account(client, world["headers2"])
    category2 = create_category(client, world["headers2"])
    client_id = "d4f740e3-6a2a-49ff-895c-3cb7f4c7e6a6"

    first = client.post("/transactions", json=_payload(category1["id"], account1["id"], client_id), headers=world["headers1"])
    second = client.post("/transactions", json=_payload(category2["id"], account2["id"], client_id), headers=world["headers2"])

    assert first.status_code == second.status_code == 201
    assert first.json()["id"] != second.json()["id"]


def test_client_id_requires_a_uuid(client, world):
    account = create_account(client, world["headers1"])
    category = create_category(client, world["headers1"])
    response = client.post(
        "/transactions",
        json=_payload(category["id"], account["id"], "not-a-uuid"),
        headers=world["headers1"],
    )

    assert response.status_code == 422


def _add_household_member(session, world) -> tuple[User, dict[str, str]]:
    member = User(email="offline-member@example.com", hashed_password="x", name="Member")
    session.add(member)
    session.flush()
    # The fixture intentionally only exposes headers; obtain the existing
    # household from the transaction owner instead of duplicating fixture data.
    owner = session.query(User).filter_by(email="offline-one@example.com").one()
    member.household_id = owner.household_id
    session.commit()
    return member, make_headers(member)


def test_private_account_client_id_replay_is_not_disclosed(client, session, world):
    owner = session.query(User).filter_by(email="offline-one@example.com").one()
    account = Account(household_id=owner.household_id, owner_id=owner.id, name="Privada", kind="cash")
    session.add(account)
    session.commit()
    category = create_category(client, world["headers1"])
    payload = _payload(category["id"], account.id, "a5b32881-666c-4335-89e9-760440d90a7e")
    assert client.post("/transactions", json=payload, headers=world["headers1"]).status_code == 201
    _, member_headers = _add_household_member(session, world)

    response = client.post("/transactions", json=payload, headers=member_headers)

    assert response.status_code == 404


def test_private_account_race_replay_is_not_disclosed(client, monkeypatch, session, world):
    owner = session.query(User).filter_by(email="offline-one@example.com").one()
    account = Account(household_id=owner.household_id, owner_id=owner.id, name="Privada", kind="cash")
    session.add(account)
    session.commit()
    category = create_category(client, world["headers1"])
    payload = _payload(category["id"], account.id, "eac2bd07-bff8-48c9-b97e-0614416e588f")
    assert client.post("/transactions", json=payload, headers=world["headers1"]).status_code == 201
    _, member_headers = _add_household_member(session, world)
    scalar = session.scalar
    first_lookup = True

    def hide_first_lookup(statement, *args, **kwargs):
        nonlocal first_lookup
        if first_lookup:
            first_lookup = False
            return None
        return scalar(statement, *args, **kwargs)

    monkeypatch.setattr(session, "scalar", hide_first_lookup)
    monkeypatch.setattr(session, "flush", lambda: (_ for _ in ()).throw(IntegrityError("", {}, Exception())))

    response = client.post("/transactions", json=payload, headers=member_headers)

    assert response.status_code == 404
