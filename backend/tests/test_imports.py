from datetime import date, datetime
import json

import pytest

from app.models import (
    Account,
    Attachment,
    Category,
    ImportBatch,
    ImportFingerprint,
    ImportRow,
    RecurringRule,
    Transaction,
    TransactionEditEvent,
    TransferGroup,
    User,
)
from tests.helpers import (
    _csv_upload,
    _mapping,
    create_account,
    create_category,
    create_transaction,
)

CSV = b'Fecha,Importe,Concepto\n31/07/2026,"MXN 1,234.50",Nomina\n01/08/2026,(20.00),Cafe\n'


def test_import_preview_normalizes_bom_currency_and_duplicate_warnings(client, session, world):
    account = create_account(client, world["headers1"])
    category = create_category(client, world["headers1"])
    create_transaction(
        client, world["headers1"], category["id"], account["id"], amount=20,
        date="2026-08-01", note="Cafe",
    )
    response = _csv_upload(
        client, "/import/preview", world["headers1"], account["id"], b"\xef\xbb\xbf" + CSV
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["suggestedMapping"] == json.loads(_mapping())
    assert payload["dateFormat"] == "DD/MM/YYYY"
    assert payload["rows"][0]["amount"] == 1234.5
    assert payload["rows"][1]["amount"] == -20
    assert payload["rows"][1]["duplicateReasons"] == ["household"]
    assert payload["rows"][1]["selected"] is False
    committed = _csv_upload(
        client, "/import/commit", world["headers1"], account["id"], CSV,
        mapping=_mapping(), dateFormat="DD/MM/YYYY", selectedPositions="[2]",
    )
    assert committed.status_code == 201
    row = session.query(ImportRow).filter_by(batch_id=committed.json()["batch"]["id"]).one()
    assert row.status == "imported"
    assert row.advisory_reasons == ["household"]


@pytest.mark.parametrize("content", [
    b"Fecha,Importe,Concepto\n31/07/2026,0,Cafe\n",
    b"Fecha,Importe,Concepto\n31/07/2026,20\n",
    b"Fecha,Importe,Concepto\n31/07/2026,20,Cafe\n\n",
])
def test_import_preview_rejects_invalid_csv_without_source_echo(client, world, content):
    account = create_account(client, world["headers1"])
    response = _csv_upload(client, "/import/preview", world["headers1"], account["id"], content)
    assert response.status_code == 422
    assert response.json() == {"detail": "CSV inválido"}


def test_import_preview_validates_mapping_date_format_and_file_rows(client, world):
    account = create_account(client, world["headers1"])
    invalid_mapping = _csv_upload(
        client, "/import/preview", world["headers1"], account["id"], CSV,
        mapping='{"date":"missing","amount":"Importe","description":"Concepto"}',
    )
    assert invalid_mapping.status_code == 422
    invalid_format = _csv_upload(
        client, "/import/preview", world["headers1"], account["id"], CSV,
        mapping=_mapping(), dateFormat="YYYY-MM-DD",
    )
    assert invalid_format.status_code == 422
    rows = b"Fecha,Importe,Concepto\n" + b"01/01/2026,1,X\n" * 1001
    assert _csv_upload(client, "/import/preview", world["headers1"], account["id"], rows).status_code == 422
    oversized_field = b"Fecha,Importe,Concepto\n01/01/2026,1," + b"X" * 10_001 + b"\n"
    assert _csv_upload(
        client, "/import/preview", world["headers1"], account["id"], oversized_field
    ).status_code == 422


def test_import_preview_hides_peer_personal_direct_duplicates_and_marks_file_and_fingerprint(client, session, world):
    account = create_account(client, world["headers1"])
    category = create_category(client, world["headers1"])
    peer = User(email="peer@example.com", hashed_password="x", name="Peer", household_id=world["h1"].id)
    session.add(peer)
    session.flush()
    private = Account(
        household_id=world["h1"].id, owner_id=peer.id, name="Privada", kind="cash", opening_balance=0,
    )
    session.add(private)
    session.flush()
    session.add(Transaction(
        household_id=world["h1"].id, type="income", amount=1234.5, category_id=category["id"],
        account_id=private.id, member_id=peer.id, date=date(2026, 7, 31), note="Nomina",
    ))
    session.commit()
    duplicate_file = CSV + b'31/07/2026,"MXN 1,234.50",Nomina\n'
    preview = _csv_upload(client, "/import/preview", world["headers1"], account["id"], duplicate_file)
    assert preview.status_code == 200
    assert preview.json()["rows"][0]["duplicateReasons"] == []
    assert preview.json()["rows"][2]["duplicateReasons"] == ["file"]

    committed = _csv_upload(
        client, "/import/commit", world["headers1"], account["id"], CSV,
        mapping=_mapping(), dateFormat="DD/MM/YYYY", selectedPositions="[1]",
    )
    assert committed.status_code == 201
    fingerprint_preview = _csv_upload(client, "/import/preview", world["headers1"], account["id"], CSV)
    assert "fingerprint" in fingerprint_preview.json()["rows"][0]["duplicateReasons"]


def test_import_preview_parses_explicit_us_dates_and_rejects_invalid_dates(client, world):
    account = create_account(client, world["headers1"])
    us_csv = b"Fecha,Importe,Concepto\n12/31/2026,1.25,Salary\n"
    preview = _csv_upload(
        client, "/import/preview", world["headers1"], account["id"], us_csv,
        mapping=_mapping(), dateFormat="MM/DD/YYYY",
    )
    assert preview.status_code == 200
    assert preview.json()["rows"][0]["date"] == "2026-12-31"
    invalid = _csv_upload(
        client, "/import/preview", world["headers1"], account["id"],
        b"Fecha,Importe,Concepto\n31/31/2026,1,Nope\n",
    )
    assert invalid.status_code == 422


def test_import_commit_reparses_upload_records_attempt_and_skips_fingerprints(client, session, world):
    account = create_account(client, world["headers1"])
    response = _csv_upload(
        client, "/import/commit", world["headers1"], account["id"], CSV,
        mapping=_mapping(), dateFormat="DD/MM/YYYY", selectedPositions="[1,2]",
    )
    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload["selectedCount"] == 2
    assert payload["importedCount"] == 2
    batch_id = payload["batch"]["id"]
    transactions = session.query(Transaction).filter_by(import_batch_id=batch_id).all()
    assert {(tx.type, float(tx.amount), tx.note) for tx in transactions} == {
        ("income", 1234.5, "Nomina"), ("expense", 20.0, "Cafe")
    }
    assert session.query(Category).filter_by(household_id=world["h1"].id, name="Unclassified").count() == 2
    income = next(tx for tx in transactions if tx.type == "income")
    assert client.patch(
        f"/transactions/{income.id}", json={"note": "Nomina corregida"}, headers=world["headers1"]
    ).status_code == 200

    retry = _csv_upload(
        client, "/import/commit", world["headers1"], account["id"], CSV,
        mapping=_mapping(), dateFormat="DD/MM/YYYY", selectedPositions="[1,2]",
    )
    assert retry.status_code == 201, retry.text
    assert retry.json()["importedCount"] == 0
    assert retry.json()["skippedCount"] == 2
    assert session.query(ImportBatch).count() == 2
    assert session.query(ImportRow).count() == 4
    assert session.query(Transaction).filter_by(import_batch_id=retry.json()["batch"]["id"]).count() == 0
    retry_row = session.query(ImportRow).filter_by(batch_id=retry.json()["batch"]["id"], source_position=1).one()
    assert retry_row.status == "skipped_fingerprint"
    assert "fingerprint" in retry_row.advisory_reasons
    assert "household" not in retry_row.advisory_reasons
    first_row = session.query(ImportRow).filter_by(batch_id=batch_id, source_position=1).one()
    assert first_row.transaction_baseline["amount"] == "1234.5000"


def test_import_batch_detail_serializes_current_state_events_and_precision(client, session, world):
    account = create_account(client, world["headers1"])
    precise_csv = b"Fecha,Importe,Concepto\n01/08/2026,0.1000,Exacta\n"
    committed = _csv_upload(
        client, "/import/commit", world["headers1"], account["id"], precise_csv,
        mapping=_mapping(), dateFormat="DD/MM/YYYY", selectedPositions="[1]",
    ).json()
    batch_id = committed["batch"]["id"]
    row = session.query(ImportRow).filter_by(batch_id=batch_id).one()
    assert row.transaction_baseline["amount"] == "0.1000"
    assert client.patch(
        f"/transactions/{row.transaction_id}", json={"note": "Editada"}, headers=world["headers1"]
    ).status_code == 200
    detail = client.get(f"/import/batches/{batch_id}", headers=world["headers1"])
    assert detail.status_code == 200
    detail_row = detail.json()["rows"][0]
    assert detail_row["currentTransaction"]["amount"] == 0.1
    assert detail_row["currentTransaction"]["note"] == "Editada"
    assert detail_row["editEvents"][0]["afterSnapshot"] == {"note": "Editada"}
    openapi = client.get("/openapi.json").json()
    assert "409" in openapi["paths"]["/import/{batch_id}/revert"]["post"]["responses"]


def test_import_commit_rejects_invalid_selection_atomically_and_private_account(client, session, world):
    account = create_account(client, world["headers1"])
    response = _csv_upload(
        client, "/import/commit", world["headers1"], account["id"], CSV,
        mapping=_mapping(), dateFormat="DD/MM/YYYY", selectedPositions="[3]",
    )
    assert response.status_code == 422
    assert session.query(ImportBatch).count() == 0
    assert _csv_upload(
        client, "/import/preview", world["headers2"], account["id"], CSV
    ).status_code == 404


def test_import_batch_detail_revert_conflict_and_restore(client, session, world):
    account = create_account(client, world["headers1"])
    committed = _csv_upload(
        client, "/import/commit", world["headers1"], account["id"], CSV,
        mapping=_mapping(), dateFormat="DD/MM/YYYY", selectedPositions="[1]",
    ).json()
    batch_id = committed["batch"]["id"]
    detail = client.get(f"/import/batches/{batch_id}", headers=world["headers1"])
    assert detail.status_code == 200
    tx_id = detail.json()["rows"][0]["transactionId"]
    assert client.get("/import/batches", headers=world["headers2"]).json() == []
    session.get(Transaction, tx_id).note = "changed"
    session.commit()
    conflict = client.post(f"/import/{batch_id}/revert", headers=world["headers1"])
    assert conflict.status_code == 409
    assert conflict.json()["detail"]["conflicts"] == [{"rowId": detail.json()["rows"][0]["id"], "transactionId": tx_id}]
    session.get(Transaction, tx_id).note = "Nomina"
    session.commit()
    reverted = client.post(f"/import/{batch_id}/revert", headers=world["headers1"])
    assert reverted.status_code == 200
    assert session.get(Transaction, tx_id).delete_reason == "import_revert"
    restored = client.post(f"/import/{batch_id}/restore", headers=world["headers1"])
    assert restored.status_code == 200
    assert session.get(Transaction, tx_id).deleted_at is None
    assert session.get(Transaction, tx_id).id == tx_id


@pytest.fixture(name="session")
def session_fixture(session_factory):
    """Issue #48: misma configuración de engine que el conftest, pero con
    ``PRAGMA foreign_keys=ON`` para cubrir el ciclo de vida de imports bajo
    FK reales de SQLite (como en Postgres). Ya no se redefine el engine."""
    yield from session_factory(foreign_keys=True)


@pytest.fixture(name="imported")
def imported_fixture(client, session, world):
    account = create_account(client, world["headers1"])
    category = create_category(client, world["headers1"])
    batch = ImportBatch(
        household_id=world["h1"].id,
        account_id=account["id"],
        created_by_id=world["u1"].id,
        source_filename="statement.csv",
        mapping={},
        selected_count=1,
        imported_count=1,
        skipped_count=0,
    )
    session.add(batch)
    session.commit()
    transaction = create_transaction(
        client,
        world["headers1"],
        category["id"],
        account["id"],
        amount=25.0,
        date="2026-07-10",
        clientId="1466a164-cd81-4d48-b704-fcfa5eb88c1b",
    )
    tx = session.get(Transaction, transaction["id"])
    tx.import_batch_id = batch.id
    session.commit()
    row = ImportRow(
        batch_id=batch.id,
        source_position=1,
        source_snapshot={},
        transaction_baseline={},
        status="imported",
        transaction_id=tx.id,
    )
    session.add(row)
    session.commit()
    session.add(ImportFingerprint(
        batch_id=batch.id,
        household_id=world["h1"].id,
        account_id=account["id"],
        fingerprint="0" * 64,
        import_row_id=row.id,
        transaction_id=tx.id,
    ))
    session.commit()
    return {"account": account, "batch": batch, "category": category, "transaction": transaction}


def _revert(session, transaction_id: str) -> None:
    tx = session.get(Transaction, transaction_id)
    tx.deleted_at = datetime(2026, 8, 5)
    tx.delete_reason = "import_revert"
    session.commit()


def test_reverted_transaction_is_hidden_from_operational_consumers(client, session, world, imported):
    tx_id = imported["transaction"]["id"]
    account_id = imported["account"]["id"]
    category_id = imported["category"]["id"]
    assert client.post(
        "/budgets", json={"categoryId": category_id, "amount": 100}, headers=world["headers1"]
    ).status_code == 201
    session.get(Transaction, tx_id).note = "reverted-report-marker"
    session.commit()
    _revert(session, tx_id)

    assert client.get("/transactions", headers=world["headers1"]).json() == []
    assert client.patch(f"/transactions/{tx_id}", json={"note": "no"}, headers=world["headers1"]).status_code == 404
    assert client.delete(f"/transactions/{tx_id}", headers=world["headers1"]).status_code == 404
    assert client.get("/accounts", headers=world["headers1"]).json()[0]["balance"] == 100.0
    assert client.patch(f"/accounts/{account_id}", json={"name": "Renombrada"}, headers=world["headers1"]).json()["balance"] == 100.0
    assert client.get("/summary/month?month=2026-07", headers=world["headers1"]).json()["expense"] == 0
    assert client.get("/summary/range?from=2026-07-01&to=2026-07-31", headers=world["headers1"]).json()["monthly"] == []
    assert client.get("/budgets/status?month=2026-07", headers=world["headers1"]).json()[0]["spent"] == 0
    report = client.get(
        "/reports/export?from=2026-07-01&to=2026-07-31&format=csv",
        headers=world["headers1"],
    )
    assert report.status_code == 200
    assert b"reverted-report-marker" not in report.content


def test_reverted_transaction_blocks_attachments_and_client_replay(client, session, world, imported):
    tx_id = imported["transaction"]["id"]
    attachment = Attachment(
        transaction_id=tx_id,
        household_id=world["h1"].id,
        filename="receipt.png",
        content_type="image/png",
        size_bytes=1,
        storage_path="missing",
    )
    session.add(attachment)
    session.commit()
    _revert(session, tx_id)

    assert client.post(
        f"/transactions/{tx_id}/attachments",
        files={"file": ("receipt.png", b"x", "image/png")},
        headers=world["headers1"],
    ).status_code == 404
    assert client.get(f"/attachments/{attachment.id}", headers=world["headers1"]).status_code == 404
    assert client.delete(f"/attachments/{attachment.id}", headers=world["headers1"]).status_code == 404
    replay = client.post(
        "/transactions",
        json={
            "clientId": imported["transaction"]["clientId"], "type": "expense", "amount": 25,
            "categoryId": imported["category"]["id"], "accountId": imported["account"]["id"],
            "date": "2026-07-10",
        },
        headers=world["headers1"],
    )
    assert replay.status_code == 409


def test_transfer_rejects_client_id_held_by_reverted_transaction(client, session, world, imported):
    _revert(session, imported["transaction"]["id"])
    destination = create_account(client, world["headers1"], name="Destino")

    response = client.post(
        "/transactions",
        json={
            "clientId": imported["transaction"]["clientId"],
            "type": "transfer",
            "amount": 25,
            "sourceAccountId": imported["account"]["id"],
            "destinationAccountId": destination["id"],
            "date": "2026-07-10",
        },
        headers=world["headers1"],
    )

    assert response.status_code == 409
    assert session.query(TransferGroup).count() == 0


def test_imported_transaction_cannot_be_deleted_and_edits_are_audited(client, session, world, imported):
    tx_id = imported["transaction"]["id"]
    assert client.delete(f"/transactions/{tx_id}", headers=world["headers1"]).status_code == 409

    response = client.patch(
        f"/transactions/{tx_id}", json={"amount": 30, "note": "corregida"}, headers=world["headers1"]
    )
    assert response.status_code == 200
    events = session.query(TransactionEditEvent).filter_by(transaction_id=tx_id).all()
    assert len(events) == 1
    assert events[0].before_snapshot == {"amount": 25.0, "note": None}
    assert events[0].after_snapshot == {"amount": 30.0, "note": "corregida"}


def _recurring_rule(session, world, imported) -> RecurringRule:
    rule = RecurringRule(
        household_id=world["h1"].id,
        type="expense",
        amount=25,
        category_id=imported["category"]["id"],
        account_id=imported["account"]["id"],
        created_by_id=world["u1"].id,
        frequency="monthly",
        next_run_date=date(2026, 9, 1),
        anchor_day=1,
    )
    session.add(rule)
    session.commit()
    return rule


def test_deleting_rule_audits_active_imported_cleanup(client, session, world, imported):
    rule = _recurring_rule(session, world, imported)
    tx = session.get(Transaction, imported["transaction"]["id"])
    tx.recurring_rule_id = rule.id
    session.commit()

    response = client.delete(f"/recurring-rules/{rule.id}", headers=world["headers1"])

    assert response.status_code == 204
    session.expire_all()
    assert session.get(Transaction, tx.id).recurring_rule_id is None
    event = session.query(TransactionEditEvent).filter_by(transaction_id=tx.id).one()
    assert event.before_snapshot == {"recurring_rule_id": rule.id}
    assert event.after_snapshot == {"recurring_rule_id": None}


def test_deleting_rule_with_reverted_transaction_preserves_its_reference(client, session, world, imported):
    rule = _recurring_rule(session, world, imported)
    tx = session.get(Transaction, imported["transaction"]["id"])
    tx.recurring_rule_id = rule.id
    session.commit()
    _revert(session, tx.id)

    response = client.delete(f"/recurring-rules/{rule.id}", headers=world["headers1"])

    assert response.status_code == 409
    session.expire_all()
    assert session.get(Transaction, tx.id).recurring_rule_id == rule.id
    assert session.get(RecurringRule, rule.id) is not None
    assert session.query(TransactionEditEvent).filter_by(transaction_id=tx.id).count() == 0


def test_deleted_history_still_blocks_category_and_account_deletion(client, session, world, imported):
    _revert(session, imported["transaction"]["id"])
    assert client.delete(
        f"/categories/{imported['category']['id']}", headers=world["headers1"]
    ).status_code == 409
    assert client.delete(
        f"/accounts/{imported['account']['id']}", headers=world["headers1"]
    ).status_code == 409
