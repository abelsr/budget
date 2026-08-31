from app.models import ReconciliationSession, Transaction
from tests.helpers import create_account, create_category, create_transaction


def _open(client, headers, account_id, balance=100, statement_date="2026-08-05"):
    return client.post(
        f"/accounts/{account_id}/reconciliations",
        json={"statementDate": statement_date, "statementBalance": balance},
        headers=headers,
    )


def test_reconciliation_calculates_difference_and_completes_only_at_zero(client, session, world):
    account = create_account(client, world["headers1"], openingBalance=100)
    category = create_category(client, world["headers1"])
    transaction = create_transaction(
        client, world["headers1"], category["id"], account["id"], amount=25,
        date="2026-08-05",
    )
    opened = _open(client, world["headers1"], account["id"], balance=75)
    assert opened.status_code == 201
    reconciliation_id = opened.json()["id"]
    resumed = _open(client, world["headers1"], account["id"], balance=75)
    assert resumed.status_code == 200
    assert resumed.json()["id"] == reconciliation_id

    detail = client.get(
        f"/accounts/{account['id']}/reconciliations/{reconciliation_id}", headers=world["headers1"],
    )
    assert detail.json()["reconciledBalance"] == 100
    assert detail.json()["pendingTotal"] == -25
    assert detail.json()["difference"] == -25
    assert client.post(
        f"/accounts/{account['id']}/reconciliations/{reconciliation_id}/complete",
        headers=world["headers1"],
    ).status_code == 409

    marked = client.post(
        f"/transactions/{transaction['id']}/reconciliation", json={"reconciled": True}, headers=world["headers1"],
    )
    assert marked.status_code == 200
    assert marked.json()["reconciliationStatus"] == "reconciled"
    completed = client.post(
        f"/accounts/{account['id']}/reconciliations/{reconciliation_id}/complete",
        headers=world["headers1"],
    )
    assert completed.status_code == 200
    assert completed.json()["status"] == "completed"
    assert session.get(Transaction, transaction["id"]).reconciliation_session_id == reconciliation_id


def test_reconciliation_respects_personal_account_visibility(client, session, world):
    account = create_account(client, world["headers1"], isPersonal=True)
    assert _open(client, world["headers2"], account["id"]).status_code == 404
    assert _open(client, world["headers1"], account["id"]).status_code == 201


def test_edit_marks_completed_reconciliation_stale(client, session, world):
    account = create_account(client, world["headers1"], openingBalance=100)
    category = create_category(client, world["headers1"])
    transaction = create_transaction(
        client, world["headers1"], category["id"], account["id"], amount=25,
        date="2026-08-05",
    )
    opened = _open(client, world["headers1"], account["id"], balance=75).json()
    client.post(
        f"/transactions/{transaction['id']}/reconciliation", json={"reconciled": True}, headers=world["headers1"],
    )
    client.post(
        f"/accounts/{account['id']}/reconciliations/{opened['id']}/complete", headers=world["headers1"],
    )
    assert client.patch(
        f"/transactions/{transaction['id']}", json={"note": "Edited"}, headers=world["headers1"],
    ).status_code == 200
    assert session.get(ReconciliationSession, opened["id"]).status == "stale"


def test_import_revert_marks_completed_reconciliation_stale(client, session, world):
    account = create_account(client, world["headers1"], openingBalance=0)
    category = create_category(client, world["headers1"])
    transaction = create_transaction(
        client, world["headers1"], category["id"], account["id"], amount=25,
        date="2026-08-05",
    )
    # The import endpoint requires a stored provenance row; this focused test
    # exercises the same soft-delete path after supplying that provenance.
    from app.models import ImportBatch, ImportRow

    batch = ImportBatch(
        household_id=world["h1"].id, account_id=account["id"], created_by_id=world["u1"].id,
        source_filename="statement.csv",
        mapping={"date": "Date", "amount": "Amount", "description": "Description"},
        selected_count=1, imported_count=1, skipped_count=0,
    )
    session.add(batch)
    session.flush()
    tx = session.get(Transaction, transaction["id"])
    tx.import_batch_id = batch.id
    session.add(ImportRow(
        batch_id=batch.id, source_position=1, source_snapshot={},
        transaction_baseline={"type": "expense", "amount": "25.0000", "category_id": category["id"], "account_id": account["id"], "date": "2026-08-05", "note": None},
        status="imported", transaction_id=tx.id,
    ))
    session.commit()
    opened = _open(client, world["headers1"], account["id"], balance=-25).json()
    assert client.post(f"/transactions/{tx.id}/reconciliation", json={"reconciled": True}, headers=world["headers1"]).status_code == 200
    assert client.post(f"/accounts/{account['id']}/reconciliations/{opened['id']}/complete", headers=world["headers1"]).status_code == 200
    assert client.post(f"/import/{batch.id}/revert", headers=world["headers1"]).status_code == 200
    assert session.get(ReconciliationSession, opened["id"]).status == "stale"


def test_transfer_sides_can_be_reconciled_independently(client, session, world):
    source = create_account(client, world["headers1"], openingBalance=100)
    destination = create_account(client, world["headers1"], name="Savings", openingBalance=0)
    transfer = client.post("/transactions", json={
        "type": "transfer", "amount": 25, "sourceAccountId": source["id"],
        "destinationAccountId": destination["id"], "date": "2026-08-05",
    }, headers=world["headers1"])
    assert transfer.status_code == 201
    source_session = _open(client, world["headers1"], source["id"], balance=75).json()
    destination_session = _open(client, world["headers1"], destination["id"], balance=25).json()
    source_row = transfer.json()["id"]
    destination_row = next(row for row in session.query(Transaction).all() if row.id != source_row)
    assert client.post(f"/transactions/{source_row}/reconciliation", json={"reconciled": True}, headers=world["headers1"]).status_code == 200
    assert client.post(f"/transactions/{destination_row.id}/reconciliation", json={"reconciled": True}, headers=world["headers1"]).status_code == 200
    assert client.post(f"/accounts/{source['id']}/reconciliations/{source_session['id']}/complete", headers=world["headers1"]).status_code == 200
    assert client.post(f"/accounts/{destination['id']}/reconciliations/{destination_session['id']}/complete", headers=world["headers1"]).status_code == 200
