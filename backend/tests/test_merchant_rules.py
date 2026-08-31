from app.models import Category, MerchantRule, Transaction
from tests.helpers import _csv_upload, _mapping, create_account, create_category


def test_rules_normalize_and_isolate_households(client, world):
    category = create_category(client, world["headers1"])
    first = client.post("/merchant-rules", json={
        "pattern": "Wálmart, S.A.", "categoryId": category["id"],
    }, headers=world["headers1"])
    assert first.status_code == 201, first.text
    assert first.json()["pattern"] == "Wálmart, S.A."
    assert client.post("/merchant-rules", json={
        "pattern": "walmart sa", "categoryId": category["id"],
    }, headers=world["headers1"]).status_code == 409
    assert client.get("/merchant-rules", headers=world["headers2"]).json() == []
    assert client.post("/merchant-rules", json={
        "pattern": "Otro", "categoryId": category["id"],
    }, headers=world["headers2"]).status_code == 404


def test_csv_import_uses_most_specific_rule_and_keeps_auditable_baseline(client, session, world):
    account = create_account(client, world["headers1"])
    groceries = create_category(client, world["headers1"], name="Despensa")
    food = create_category(client, world["headers1"], name="Restaurantes")
    client.post("/merchant-rules", json={"pattern": "Walmart", "categoryId": groceries["id"]}, headers=world["headers1"])
    client.post("/merchant-rules", json={"pattern": "Walmart Express", "categoryId": food["id"]}, headers=world["headers1"])
    csv = b"Fecha,Importe,Concepto\n01/08/2026,-20.00,WALMART EXPRESS 123\n02/08/2026,-10.00,Walmart Supercenter\n"
    result = _csv_upload(
        client, "/import/commit", world["headers1"], account["id"], csv,
        mapping=_mapping(), dateFormat="DD/MM/YYYY", selectedPositions="[1,2]",
    )
    assert result.status_code == 201, result.text
    rows = session.query(MerchantRule).filter_by(household_id=world["h1"].id).all()
    assert len(rows) == 2
    batch_id = result.json()["batch"]["id"]
    imported = session.query(Category.name).join(Transaction).filter(Transaction.import_batch_id == batch_id).all()
    assert {name for (name,) in imported} == {"Restaurantes", "Despensa"}


def test_deleting_category_removes_its_merchant_rules(client, session, world):
    category = create_category(client, world["headers1"], name="Temporal")
    created = client.post("/merchant-rules", json={"pattern": "Temporal", "categoryId": category["id"]}, headers=world["headers1"])
    assert created.status_code == 201
    assert client.delete(f"/categories/{category['id']}", headers=world["headers1"]).status_code == 204
    assert session.query(MerchantRule).filter_by(id=created.json()["id"]).count() == 0
