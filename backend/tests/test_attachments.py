from datetime import date

import pytest

from app.models import Attachment, Transaction
from app.services import storage

PNG_BYTES = b"\x89PNG\r\n\x1a\nfake-png-content"


@pytest.fixture(name="world")
def world_fixture(session, world_factory, monkeypatch):
    """Dos hogares, cada uno con usuario, cuenta, categoría y transacción.
    Sustituye el storage S3 por un fake en memoria (dict)."""
    store: dict[str, bytes] = {}

    def fake_put(object_key: str, data: bytes, content_type: str) -> None:
        store[object_key] = data

    def fake_get(object_key: str) -> bytes:
        if object_key not in store:
            raise storage.StorageError(f"no existe: {object_key}")
        return store[object_key]

    def fake_delete(object_key: str) -> None:
        store.pop(object_key, None)

    monkeypatch.setattr(storage, "put_attachment", fake_put)
    monkeypatch.setattr(storage, "get_attachment", fake_get)
    monkeypatch.setattr(storage, "delete_attachment", fake_delete)

    world = world_factory(
        accounts=(
            {"household": 1, "name": "Efectivo", "kind": "cash"},
            {"household": 2, "name": "Efectivo", "kind": "cash"},
        ),
        categories=(
            {"household": 1, "name": "Comida", "icon": "utensils", "color": "#30b0c7", "type": "expense"},
            {"household": 2, "name": "Comida", "icon": "utensils", "color": "#30b0c7", "type": "expense"},
        ),
    )
    for index in (0, 1):
        tx = Transaction(
            household_id=world[f"h{index + 1}"].id,
            type="expense",
            amount=10.0,
            category_id=world["categories"][index].id,
            account_id=world["accounts"][index].id,
            member_id=world[f"u{index + 1}"].id,
            date=date(2026, 7, 10),
        )
        world[f"tx{index + 1}"] = tx
        session.add(tx)
        session.commit()
    world["store"] = store
    return world


def upload(client, headers, tx_id, content=PNG_BYTES, filename="ticket.png", content_type="image/png"):
    return client.post(
        f"/transactions/{tx_id}/attachments",
        files={"file": (filename, content, content_type)},
        headers=headers,
    )


def test_upload_attachment_and_list_in_transaction(client, world):
    resp = upload(client, world["headers1"], world["tx1"].id)
    assert resp.status_code == 201, resp.text
    attachment = resp.json()
    assert set(attachment.keys()) == {
        "id",
        "transactionId",
        "filename",
        "contentType",
        "sizeBytes",
        "createdAt",
    }
    assert attachment["transactionId"] == world["tx1"].id
    assert attachment["filename"] == "ticket.png"
    assert attachment["contentType"] == "image/png"
    assert attachment["sizeBytes"] == len(PNG_BYTES)

    # El objeto existe en el storage bajo la key {household_id}/{attachment_id}.png
    assert len(world["store"]) == 1
    object_key = f"{world['h1'].id}/{attachment['id']}.png"
    assert world["store"][object_key] == PNG_BYTES

    # La transacción incluye el adjunto
    resp = client.get("/transactions", headers=world["headers1"])
    assert resp.status_code == 200
    tx = resp.json()[0]
    assert tx["id"] == world["tx1"].id
    assert [a["id"] for a in tx["attachments"]] == [attachment["id"]]


def test_upload_to_foreign_transaction_returns_404(client, world):
    resp = upload(client, world["headers1"], world["tx2"].id)
    assert resp.status_code == 404


def test_upload_disallowed_content_type_returns_415(client, world):
    resp = upload(
        client,
        world["headers1"],
        world["tx1"].id,
        content=b"hola",
        filename="nota.txt",
        content_type="text/plain",
    )
    assert resp.status_code == 415


def test_upload_over_10mb_returns_413(client, world):
    big = b"x" * (10 * 1024 * 1024 + 1)
    resp = upload(
        client,
        world["headers1"],
        world["tx1"].id,
        content=big,
        filename="grande.png",
        content_type="image/png",
    )
    assert resp.status_code == 413


def test_upload_storage_failure_returns_502_and_no_record(client, world, session, monkeypatch):
    def failing_put(object_key: str, data: bytes, content_type: str) -> None:
        raise storage.StorageError("S3 caído")

    monkeypatch.setattr(storage, "put_attachment", failing_put)

    resp = upload(client, world["headers1"], world["tx1"].id)
    assert resp.status_code == 502
    assert resp.json() == {"detail": "Error al guardar el comprobante"}

    # No queda registro en la base de datos
    session.expire_all()
    assert session.query(Attachment).count() == 0


def test_download_attachment_returns_same_bytes(client, world):
    attachment = upload(client, world["headers1"], world["tx1"].id).json()

    resp = client.get(f"/attachments/{attachment['id']}", headers=world["headers1"])
    assert resp.status_code == 200
    assert resp.content == PNG_BYTES
    assert resp.headers["content-type"] == "image/png"
    assert "ticket.png" in resp.headers["content-disposition"]


def test_download_foreign_attachment_returns_404(client, world):
    attachment = upload(client, world["headers1"], world["tx1"].id).json()

    resp = client.get(f"/attachments/{attachment['id']}", headers=world["headers2"])
    assert resp.status_code == 404


def test_delete_attachment_removes_file_and_record(client, world):
    headers = world["headers1"]
    attachment = upload(client, headers, world["tx1"].id).json()
    assert len(world["store"]) == 1

    resp = client.delete(f"/attachments/{attachment['id']}", headers=headers)
    assert resp.status_code == 204
    assert len(world["store"]) == 0

    resp = client.get(f"/attachments/{attachment['id']}", headers=headers)
    assert resp.status_code == 404

    tx = client.get("/transactions", headers=headers).json()[0]
    assert tx["attachments"] == []
