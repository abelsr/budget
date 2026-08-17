from app.models import Transaction, TransferGroup
from tests.test_core import create_account, create_category, world_fixture

world = world_fixture


def transfer_payload(source_id: str, destination_id: str, **overrides):
    payload = {
        "type": "transfer",
        "amount": 500,
        "sourceAccountId": source_id,
        "destinationAccountId": destination_id,
        "date": "2026-08-05",
        "note": "Ahorro del mes",
    }
    payload.update(overrides)
    return payload


def test_transfer_creates_linked_rows_and_preserves_household_total(client, session, world):
    source = create_account(client, world["headers1"], name="Efectivo", openingBalance=1000)
    destination = create_account(client, world["headers1"], name="Ahorro", kind="savings", openingBalance=200)

    response = client.post("/transactions", json=transfer_payload(source["id"], destination["id"]), headers=world["headers1"])

    assert response.status_code == 201, response.text
    created = response.json()
    assert created["type"] == "transfer"
    assert created["transferDirection"] == "outflow"
    assert created["categoryId"] is None
    assert created["counterpartyAccountId"] == destination["id"]
    assert session.query(TransferGroup).count() == 1
    rows = session.query(Transaction).all()
    assert len(rows) == 2
    assert {row.transfer_direction for row in rows} == {"outflow", "inflow"}
    assert {row.account_id for row in rows} == {source["id"], destination["id"]}
    assert all(row.category_id is None and row.transfer_group_id == created["transferGroupId"] for row in rows)

    balances = {account["id"]: account["balance"] for account in client.get("/accounts", headers=world["headers1"]).json()}
    assert balances[source["id"]] == 500
    assert balances[destination["id"]] == 700
    assert sum(balances.values()) == 1200


def test_transfer_is_hidden_by_default_and_excluded_from_summary(client, world):
    source = create_account(client, world["headers1"])
    destination = create_account(client, world["headers1"], name="Ahorro", kind="savings")
    category = create_category(client, world["headers1"])
    client.post("/transactions", json=transfer_payload(source["id"], destination["id"]), headers=world["headers1"])
    client.post("/transactions", json={"type": "expense", "amount": 25, "categoryId": category["id"], "accountId": source["id"], "date": "2026-08-05"}, headers=world["headers1"])

    assert len(client.get("/transactions", headers=world["headers1"]).json()) == 1
    transfers = client.get("/transactions", params={"type": "transfer"}, headers=world["headers1"])
    assert len(transfers.json()) == 2
    summary = client.get("/summary/month", params={"month": "2026-08"}, headers=world["headers1"]).json()
    assert summary == {"income": 0.0, "expense": 25.0, "byCategory": [{"categoryId": category["id"], "total": 25.0}]}


def test_transfer_replays_by_group_and_deletes_atomically(client, session, world):
    source = create_account(client, world["headers1"])
    destination = create_account(client, world["headers1"], name="Ahorro", kind="savings")
    payload = transfer_payload(source["id"], destination["id"], clientId="7705148a-f9e7-426f-b8f7-fd77b28bca05")
    first = client.post("/transactions", json=payload, headers=world["headers1"])
    retry = client.post("/transactions", json=payload, headers=world["headers1"])

    assert first.status_code == retry.status_code == 201
    assert first.json()["id"] == retry.json()["id"]
    assert session.query(TransferGroup).count() == 1
    rows = session.query(Transaction).all()
    assert len(rows) == 2
    response = client.delete(f"/transactions/{rows[1].id}", headers=world["headers1"])
    assert response.status_code == 204
    # soft delete: both rows stay (hidden) and the group keeps its client_id guard
    rows = session.query(Transaction).all()
    assert len(rows) == 2
    assert all(row.deleted_at is not None and row.delete_reason == "manual" for row in rows)
    assert session.query(TransferGroup).count() == 1
    # a replay of the same client_id still collides
    replay = client.post("/transactions", json=payload, headers=world["headers1"])
    assert replay.status_code == 409


def test_transfer_rejects_invalid_or_single_account_payloads(client, world):
    source = create_account(client, world["headers1"])
    category = create_category(client, world["headers1"])
    same_account = client.post("/transactions", json=transfer_payload(source["id"], source["id"]), headers=world["headers1"])
    assert same_account.status_code == 422
    category_payload = transfer_payload(source["id"], "other", categoryId=category["id"])
    assert client.post("/transactions", json=category_payload, headers=world["headers1"]).status_code == 422


def test_transfer_client_id_cannot_collide_with_regular_transaction(client, world):
    source = create_account(client, world["headers1"])
    destination = create_account(client, world["headers1"], name="Ahorro", kind="savings")
    category = create_category(client, world["headers1"])
    client_id = "75cda6ca-80b4-43b7-96eb-0866f100c15a"
    regular = {
        "type": "expense", "amount": 10, "categoryId": category["id"],
        "accountId": source["id"], "date": "2026-08-05", "clientId": client_id,
    }
    assert client.post("/transactions", json=regular, headers=world["headers1"]).status_code == 201
    response = client.post("/transactions", json=transfer_payload(source["id"], destination["id"], clientId=client_id), headers=world["headers1"])
    assert response.status_code == 409
