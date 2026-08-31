from tests.helpers import create_account, create_category, create_transaction


# ---------- Cuentas ----------


def test_account_crud(client, world):
    headers = world["headers1"]

    resp = client.post(
        "/accounts",
        json={"name": "Débito", "kind": "debit", "openingBalance": 250.5},
        headers=headers,
    )
    assert resp.status_code == 201
    account = resp.json()
    assert account["balance"] == 250.5
    assert account["householdId"] == world["h1"].id
    assert account["kind"] == "debit"

    resp = client.get("/accounts", headers=headers)
    assert resp.status_code == 200
    assert [a["id"] for a in resp.json()] == [account["id"]]

    resp = client.patch(
        f"/accounts/{account['id']}",
        json={"name": "Débito Principal", "kind": "savings"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Débito Principal"
    assert resp.json()["kind"] == "savings"
    assert resp.json()["balance"] == 250.5

    resp = client.delete(f"/accounts/{account['id']}", headers=headers)
    assert resp.status_code == 204
    assert client.get("/accounts", headers=headers).json() == []


def test_account_kind_validation(client, world):
    resp = client.post(
        "/accounts",
        json={"name": "X", "kind": "wallet", "openingBalance": 0},
        headers=world["headers1"],
    )
    assert resp.status_code == 422


def test_account_delete_with_transactions_returns_409(client, world):
    headers = world["headers1"]
    account = create_account(client, headers)
    category = create_category(client, headers)
    create_transaction(client, headers, category["id"], account["id"])

    resp = client.delete(f"/accounts/{account['id']}", headers=headers)
    assert resp.status_code == 409
    assert resp.json()["detail"] == "La cuenta tiene movimientos"


# ---------- Categorías ----------


def test_category_crud(client, world):
    headers = world["headers1"]

    resp = client.post(
        "/categories",
        json={"name": "Comida", "icon": "utensils", "color": "#30b0c7", "type": "expense"},
        headers=headers,
    )
    assert resp.status_code == 201
    category = resp.json()
    assert category["active"] is True
    assert category["householdId"] == world["h1"].id

    resp = client.get("/categories", headers=headers)
    assert resp.status_code == 200
    assert [c["id"] for c in resp.json()] == [category["id"]]

    resp = client.patch(
        f"/categories/{category['id']}",
        json={"name": "Restaurantes", "active": False},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Restaurantes"
    assert resp.json()["active"] is False

    resp = client.delete(f"/categories/{category['id']}", headers=headers)
    assert resp.status_code == 204
    assert client.get("/categories", headers=headers).json() == []


def test_category_color_and_type_validation(client, world):
    headers = world["headers1"]
    resp = client.post(
        "/categories",
        json={"name": "X", "icon": "tag", "color": "rojo", "type": "expense"},
        headers=headers,
    )
    assert resp.status_code == 422
    resp = client.post(
        "/categories",
        json={"name": "X", "icon": "tag", "color": "#30b0c7", "type": "otro"},
        headers=headers,
    )
    assert resp.status_code == 422


def test_category_delete_with_transactions_returns_409(client, world):
    headers = world["headers1"]
    account = create_account(client, headers)
    category = create_category(client, headers)
    create_transaction(client, headers, category["id"], account["id"])

    resp = client.delete(f"/categories/{category['id']}", headers=headers)
    assert resp.status_code == 409
    assert resp.json()["detail"] == "La categoría tiene movimientos"


# ---------- Transacciones y balance ----------


def test_transactions_affect_account_balance(client, world):
    headers = world["headers1"]
    account = create_account(client, headers, openingBalance=100.0)
    expense_cat = create_category(client, headers)
    income_cat = create_category(client, headers, name="Sueldo", type="income", icon="banknote")

    create_transaction(
        client, headers, expense_cat["id"], account["id"], amount=30.0, type="expense"
    )
    accounts = client.get("/accounts", headers=headers).json()
    assert accounts[0]["balance"] == 70.0

    create_transaction(
        client, headers, income_cat["id"], account["id"], amount=50.0, type="income"
    )
    accounts = client.get("/accounts", headers=headers).json()
    assert accounts[0]["balance"] == 120.0


def test_transaction_crud_and_order_and_month_filter(client, world):
    headers = world["headers1"]
    account = create_account(client, headers)
    category = create_category(client, headers)

    tx_june = create_transaction(client, headers, category["id"], account["id"], date="2026-06-15")
    tx_july_old = create_transaction(client, headers, category["id"], account["id"], date="2026-07-01")
    tx_july_new = create_transaction(client, headers, category["id"], account["id"], date="2026-07-20")

    resp = client.get("/transactions", headers=headers)
    assert resp.status_code == 200
    dates = [t["date"] for t in resp.json()]
    assert dates == ["2026-07-20", "2026-07-01", "2026-06-15"]

    resp = client.get("/transactions", params={"month": "2026-07"}, headers=headers)
    assert resp.status_code == 200
    ids = {t["id"] for t in resp.json()}
    assert ids == {tx_july_old["id"], tx_july_new["id"]}
    assert tx_june["id"] not in ids

    resp = client.get("/transactions", params={"month": "bad-month"}, headers=headers)
    assert resp.status_code == 422

    # PATCH parcial
    resp = client.patch(
        f"/transactions/{tx_june['id']}",
        json={"amount": 99.5, "note": "ajuste"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["amount"] == 99.5
    assert resp.json()["note"] == "ajuste"
    assert resp.json()["date"] == "2026-06-15"

    # DELETE
    resp = client.delete(f"/transactions/{tx_june['id']}", headers=headers)
    assert resp.status_code == 204
    assert len(client.get("/transactions", headers=headers).json()) == 2


def test_transaction_validation(client, world):
    headers = world["headers1"]
    account = create_account(client, headers)
    category = create_category(client, headers)

    # amount debe ser > 0
    resp = client.post(
        "/transactions",
        json={
            "type": "expense",
            "amount": 0,
            "categoryId": category["id"],
            "accountId": account["id"],
            "date": "2026-07-10",
        },
        headers=headers,
    )
    assert resp.status_code == 422

    # cuenta inexistente
    resp = client.post(
        "/transactions",
        json={
            "type": "expense",
            "amount": 5,
            "categoryId": category["id"],
            "accountId": "no-existe",
            "date": "2026-07-10",
        },
        headers=headers,
    )
    assert resp.status_code == 404


def test_transaction_author_is_authenticated_user_not_member_id(client, world):
    account = create_account(client, world["headers1"])
    category = create_category(client, world["headers1"])
    transaction = create_transaction(
        client,
        world["headers1"],
        category["id"],
        account["id"],
        memberId=world["u2"].id,
    )
    assert transaction["memberId"] == world["u1"].id

    response = client.patch(
        f"/transactions/{transaction['id']}",
        json={"note": "actualizado", "memberId": world["u2"].id},
        headers=world["headers1"],
    )
    assert response.status_code == 200
    assert response.json()["memberId"] == world["u1"].id


def test_transaction_filters_and_month_range_conflict(client, world):
    headers = world["headers1"]
    account = create_account(client, headers, name="Efectivo")
    other_account = create_account(client, headers, name="Débito")
    category = create_category(client, headers, name="Comida")
    income_category = create_category(client, headers, name="Nómina", type="income")
    grocery = create_transaction(client, headers, category["id"], account["id"], amount=30,
                                 date="2026-07-10", note="Súper mercado")
    create_transaction(client, headers, category["id"], other_account["id"], amount=15,
                       date="2026-06-10", note="Café")
    salary = create_transaction(client, headers, income_category["id"], account["id"], amount=100,
                                type="income", date="2026-07-20", note="Nómina")

    response = client.get(
        "/transactions",
        params={"q": "MERCADO", "categoryId": category["id"], "accountId": account["id"],
                "type": "expense", "from": "2026-07-01", "to": "2026-07-31"},
        headers=headers,
    )
    assert response.status_code == 200
    assert [tx["id"] for tx in response.json()] == [grocery["id"]]

    response = client.get(
        "/transactions",
        params={"month": "2026-07", "from": "2026-01-01", "to": "2026-01-02"},
        headers=headers,
    )
    assert response.status_code == 422
    assert response.json()["detail"] == "month no se puede combinar con from ni to"


# ---------- Aislamiento entre hogares ----------


def test_household_isolation(client, world):
    headers1 = world["headers1"]
    headers2 = world["headers2"]

    account = create_account(client, headers1)
    category = create_category(client, headers1)
    tx = create_transaction(client, headers1, category["id"], account["id"])

    # El otro hogar no ve nada
    assert client.get("/accounts", headers=headers2).json() == []
    assert client.get("/transactions", headers=headers2).json() == []
    categories2 = client.get("/categories", headers=headers2).json()
    assert all(c["householdId"] == world["h2"].id for c in categories2)

    # Operar sobre ids ajenos → 404
    assert client.get(f"/accounts", headers=headers2).status_code == 200
    assert client.patch(f"/accounts/{account['id']}", json={"name": "X"}, headers=headers2).status_code == 404
    assert client.delete(f"/accounts/{account['id']}", headers=headers2).status_code == 404
    assert client.patch(f"/categories/{category['id']}", json={"name": "X"}, headers=headers2).status_code == 404
    assert client.delete(f"/categories/{category['id']}", headers=headers2).status_code == 404
    assert client.patch(f"/transactions/{tx['id']}", json={"note": "X"}, headers=headers2).status_code == 404
    assert client.delete(f"/transactions/{tx['id']}", headers=headers2).status_code == 404


def test_transaction_with_foreign_category_returns_404(client, world):
    headers1 = world["headers1"]
    account = create_account(client, headers1)
    foreign_category = create_category(client, world["headers2"], name="Cat Ajena")

    resp = client.post(
        "/transactions",
        json={
            "type": "expense",
            "amount": 10.0,
            "categoryId": foreign_category["id"],
            "accountId": account["id"],
            "date": "2026-07-10",
        },
        headers=headers1,
    )
    assert resp.status_code == 404
