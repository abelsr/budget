import jwt
import pytest
from datetime import date, datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.config import settings
from app.models import Account, Category, Household, Invitation, Transaction, User


def _auth_headers(user: User) -> dict[str, str]:
    token = jwt.encode(
        {"sub": user.id, "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    return {"Authorization": f"Bearer {token}"}


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _make_user(session: Session, email: str, name: str) -> User:
    user = User(
        email=email,
        hashed_password="x",
        name=name,
    )
    session.add(user)
    session.flush()
    return user


@pytest.fixture(name="setup_data")
def setup_data_fixture(session: Session):
    """Hogar principal con 2 usuarios, cuenta y 2 categorías; y un segundo hogar."""
    user = _make_user(session, "ana@example.com", "Ana")
    member2 = _make_user(session, "luis@example.com", "Luis")
    other_user = _make_user(session, "otro@example.com", "Otro")
    household = Household(name="Familia Pérez", currency_code="MXN", owner_id=user.id)
    other_household = Household(
        name="Otro Hogar", currency_code="USD", owner_id=other_user.id
    )
    session.add_all([household, other_household])
    session.flush()
    user.household_id = household.id
    member2.household_id = household.id
    other_user.household_id = other_household.id

    account = Account(household_id=household.id, name="Débito", kind="debit")
    other_account = Account(household_id=other_household.id, name="Cash", kind="cash")
    session.add_all([account, other_account])
    session.flush()

    cat_food = Category(
        household_id=household.id, name="Comida", icon="pizza", color="#30b0c7", type="expense"
    )
    cat_transport = Category(
        household_id=household.id, name="Transporte", icon="car", color="#ff0000", type="expense"
    )
    cat_salary = Category(
        household_id=household.id, name="Salario", icon="briefcase", color="#00ff00", type="income"
    )
    other_cat = Category(
        household_id=other_household.id, name="Ajena", icon="x", color="#000000", type="expense"
    )
    session.add_all([cat_food, cat_transport, cat_salary, other_cat])
    session.commit()

    return {
        "household": household,
        "other_household": other_household,
        "user": user,
        "member2": member2,
        "other_user": other_user,
        "account": account,
        "other_account": other_account,
        "cat_food": cat_food,
        "cat_transport": cat_transport,
        "cat_salary": cat_salary,
        "other_cat": other_cat,
    }


def test_get_my_household(client, setup_data):
    data = setup_data
    response = client.get("/households/me", headers=_auth_headers(data["user"]))
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == data["household"].id
    assert body["name"] == "Familia Pérez"
    assert body["currencyCode"] == "MXN"
    assert body["isOwner"] is True


def test_get_my_household_members(client, setup_data):
    data = setup_data
    response = client.get("/households/me/members", headers=_auth_headers(data["user"]))
    assert response.status_code == 200
    members = response.json()
    assert [m["email"] for m in members] == ["ana@example.com", "luis@example.com"]
    assert members[0]["isOwner"] is True
    assert members[1]["isOwner"] is False
    for member in members:
        assert set(member.keys()) == {"id", "name", "email", "isOwner"}

    response = client.get("/households/me/members", headers=_auth_headers(data["member2"]))
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_create_invitation(client, session, setup_data):
    data = setup_data
    before = datetime.now(timezone.utc).replace(tzinfo=None)
    response = client.post("/households/me/invitations", headers=_auth_headers(data["user"]))
    after = datetime.now(timezone.utc).replace(tzinfo=None)

    assert response.status_code == 201
    body = response.json()
    assert body["token"]
    assert body["token"] in body["inviteUrl"]
    assert body["inviteUrl"] == f"/login?invite={body['token']}"
    assert "expiresAt" in body

    invitation = session.query(Invitation).filter_by(token=body["token"]).one()
    assert invitation.household_id == data["household"].id
    assert invitation.created_by_id == data["user"].id
    assert before + timedelta(days=7) <= invitation.expires_at <= after + timedelta(days=7)


def test_create_invitation_enforces_active_limit(client, setup_data, monkeypatch):
    data = setup_data
    monkeypatch.setattr(settings, "max_active_invitations_per_household", 1)

    assert client.post(
        "/households/me/invitations", headers=_auth_headers(data["user"])
    ).status_code == 201
    response = client.post(
        "/households/me/invitations", headers=_auth_headers(data["user"])
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "Este hogar alcanzó el máximo de invitaciones activas"


def test_only_owner_can_administer_invitations(client, session, setup_data, monkeypatch):
    data = setup_data
    member_headers = _auth_headers(data["member2"])
    assert client.post("/households/me/invitations", headers=member_headers).status_code == 403
    assert client.get("/households/me/invitations", headers=member_headers).status_code == 403

    active = Invitation(
        household_id=data["household"].id,
        created_by_id=data["user"].id,
        expires_at=_now() + timedelta(days=1),
    )
    expired = Invitation(
        household_id=data["household"].id,
        created_by_id=data["user"].id,
        expires_at=_now() - timedelta(days=1),
    )
    used = Invitation(
        household_id=data["household"].id,
        created_by_id=data["user"].id,
        expires_at=_now() + timedelta(days=1),
        used_at=_now(),
    )
    session.add_all([active, expired, used])
    session.commit()

    response = client.get("/households/me/invitations", headers=_auth_headers(data["user"]))
    assert response.status_code == 200
    assert response.json() == [{
        "id": active.id,
        "expiresAt": active.expires_at.isoformat(),
        "createdAt": active.created_at.isoformat(),
    }]

    locked_queries = []
    original_scalar = session.scalar

    def capture_scalar(statement, *args, **kwargs):
        if getattr(statement, "_for_update_arg", None) is not None:
            locked_queries.append(statement)
        return original_scalar(statement, *args, **kwargs)

    monkeypatch.setattr(session, "scalar", capture_scalar)
    assert client.delete(
        f"/households/me/invitations/{active.id}", headers=_auth_headers(data["user"])
    ).status_code == 204
    # SQLite no aplica bloqueos de fila; esta aserción conserva la intención de
    # serialización que se ejecuta como FOR UPDATE en PostgreSQL.
    assert locked_queries
    assert client.delete(
        f"/households/me/invitations/{expired.id}", headers=_auth_headers(data["user"])
    ).status_code == 404


def test_member_cannot_revoke_an_owner_invitation(client, session, setup_data):
    data = setup_data
    response = client.post(
        "/households/me/invitations", headers=_auth_headers(data["user"])
    )
    assert response.status_code == 201
    invitation = session.query(Invitation).filter_by(token=response.json()["token"]).one()

    response = client.delete(
        f"/households/me/invitations/{invitation.id}",
        headers=_auth_headers(data["member2"]),
    )
    assert response.status_code == 403
    assert session.get(Invitation, invitation.id) is not None


def test_invitation_lock_query_is_scoped_to_owner_household(
    client, session, setup_data, monkeypatch
):
    data = setup_data
    invitation = Invitation(
        household_id=data["other_household"].id,
        created_by_id=data["other_user"].id,
        expires_at=_now() + timedelta(days=1),
    )
    session.add(invitation)
    session.commit()

    locked_queries = []
    original_scalar = session.scalar

    def capture_scalar(statement, *args, **kwargs):
        if getattr(statement, "_for_update_arg", None) is not None:
            locked_queries.append(statement)
        return original_scalar(statement, *args, **kwargs)

    monkeypatch.setattr(session, "scalar", capture_scalar)
    response = client.delete(
        f"/households/me/invitations/{invitation.id}",
        headers=_auth_headers(data["user"]),
    )
    assert response.status_code == 404
    assert len(locked_queries) == 1
    params = locked_queries[0].compile().params.values()
    assert invitation.id in params
    assert data["household"].id in params


def test_member_lock_query_is_scoped_to_owner_household(
    client, session, setup_data, monkeypatch
):
    data = setup_data
    locked_queries = []
    original_scalar = session.scalar

    def capture_scalar(statement, *args, **kwargs):
        if getattr(statement, "_for_update_arg", None) is not None:
            locked_queries.append(statement)
        return original_scalar(statement, *args, **kwargs)

    monkeypatch.setattr(session, "scalar", capture_scalar)
    response = client.delete(
        f"/households/me/members/{data['other_user'].id}",
        headers=_auth_headers(data["user"]),
    )
    assert response.status_code == 404
    assert len(locked_queries) == 1
    params = locked_queries[0].compile().params.values()
    assert data["other_user"].id in params
    assert data["household"].id in params


def test_owner_can_detach_member_without_losing_authorship(
    client, session, setup_data, monkeypatch
):
    data = setup_data
    created = client.post(
        "/transactions",
        headers=_auth_headers(data["member2"]),
        json={
            "type": "expense",
            "amount": 10,
            "categoryId": data["cat_food"].id,
            "accountId": data["account"].id,
            "date": date.today().isoformat(),
        },
    )
    assert created.status_code == 201
    transaction_id = created.json()["id"]

    locked_queries = []
    original_scalar = session.scalar

    def capture_scalar(statement, *args, **kwargs):
        if getattr(statement, "_for_update_arg", None) is not None:
            locked_queries.append(statement)
        return original_scalar(statement, *args, **kwargs)

    monkeypatch.setattr(session, "scalar", capture_scalar)

    response = client.delete(
        f"/households/me/members/{data['member2'].id}", headers=_auth_headers(data["user"])
    )
    assert response.status_code == 204
    session.refresh(data["member2"])
    assert data["member2"].household_id is None
    assert session.get(User, data["member2"].id) is not None
    transactions = client.get("/transactions", headers=_auth_headers(data["user"]))
    assert transactions.status_code == 200
    transaction = next(row for row in transactions.json() if row["id"] == transaction_id)
    assert transaction["memberId"] == data["member2"].id
    assert transaction["authorName"] == "Luis"
    # El miembro objetivo se carga con FOR UPDATE. SQLite no aplica el bloqueo,
    # pero PostgreSQL serializa intentos de expulsión sobre la misma fila.
    assert any(
        data["member2"].id in statement.compile().params.values()
        for statement in locked_queries
    )


def test_member_removal_rejects_owner_and_foreign_or_nonowner_requests(client, setup_data):
    data = setup_data
    owner_headers = _auth_headers(data["user"])
    assert client.delete(
        f"/households/me/members/{data['user'].id}", headers=owner_headers
    ).status_code == 409
    assert client.delete(
        f"/households/me/members/{data['other_user'].id}", headers=owner_headers
    ).status_code == 404
    assert client.delete(
        f"/households/me/members/{data['user'].id}", headers=_auth_headers(data["member2"])
    ).status_code == 403


def _add_transaction(
    session: Session, *, household, account, category, member, tx_type, amount, tx_date
):
    tx = Transaction(
        household_id=household.id,
        type=tx_type,
        amount=amount,
        category_id=category.id,
        account_id=account.id,
        member_id=member.id,
        date=tx_date,
    )
    session.add(tx)
    return tx


def test_month_summary_current_month(client, session, setup_data):
    data = setup_data
    today = date.today()
    day = date(today.year, today.month, 15)

    _add_transaction(session, household=data["household"], account=data["account"],
                     category=data["cat_food"], member=data["user"],
                     tx_type="expense", amount=100.0, tx_date=day)
    _add_transaction(session, household=data["household"], account=data["account"],
                     category=data["cat_food"], member=data["member2"],
                     tx_type="expense", amount=50.5, tx_date=day)
    _add_transaction(session, household=data["household"], account=data["account"],
                     category=data["cat_transport"], member=data["user"],
                     tx_type="expense", amount=200.0, tx_date=day)
    _add_transaction(session, household=data["household"], account=data["account"],
                     category=data["cat_salary"], member=data["user"],
                     tx_type="income", amount=1000.0, tx_date=day)
    session.commit()

    response = client.get("/summary/month", headers=_auth_headers(data["user"]))
    assert response.status_code == 200
    body = response.json()
    assert body["income"] == 1000.0
    assert body["expense"] == 350.5

    by_category = body["byCategory"]
    assert len(by_category) == 2
    # Orden DESC por total: transporte (200) antes que comida (150.5)
    assert by_category[0]["categoryId"] == data["cat_transport"].id
    assert by_category[0]["total"] == 200.0
    assert by_category[1]["categoryId"] == data["cat_food"].id
    assert by_category[1]["total"] == 150.5


def test_month_summary_empty_month(client, session, setup_data):
    data = setup_data
    response = client.get(
        "/summary/month", params={"month": "2000-01"}, headers=_auth_headers(data["user"])
    )
    assert response.status_code == 200
    assert response.json() == {"income": 0.0, "expense": 0.0, "byCategory": []}


def test_month_summary_isolation_between_households(client, session, setup_data):
    data = setup_data
    today = date.today()
    day = date(today.year, today.month, 10)

    # Transacción del hogar principal
    _add_transaction(session, household=data["household"], account=data["account"],
                     category=data["cat_food"], member=data["user"],
                     tx_type="expense", amount=100.0, tx_date=day)
    # Transacciones del OTRO hogar (mismo mes)
    _add_transaction(session, household=data["other_household"], account=data["other_account"],
                     category=data["other_cat"], member=data["other_user"],
                     tx_type="expense", amount=9999.0, tx_date=day)
    _add_transaction(session, household=data["other_household"], account=data["other_account"],
                     category=data["other_cat"], member=data["other_user"],
                     tx_type="income", amount=8888.0, tx_date=day)
    session.commit()

    response = client.get("/summary/month", headers=_auth_headers(data["user"]))
    assert response.status_code == 200
    body = response.json()
    assert body["income"] == 0.0
    assert body["expense"] == 100.0
    assert len(body["byCategory"]) == 1
    assert body["byCategory"][0]["categoryId"] == data["cat_food"].id
    assert body["byCategory"][0]["total"] == 100.0


def test_range_summary_groups_months_categories_and_isolates_households(client, session, setup_data):
    data = setup_data
    _add_transaction(session, household=data["household"], account=data["account"],
                     category=data["cat_salary"], member=data["user"],
                     tx_type="income", amount=1200.0, tx_date=date(2026, 1, 31))
    _add_transaction(session, household=data["household"], account=data["account"],
                     category=data["cat_food"], member=data["member2"],
                     tx_type="expense", amount=200.0, tx_date=date(2026, 2, 1))
    _add_transaction(session, household=data["household"], account=data["account"],
                     category=data["cat_transport"], member=data["user"],
                     tx_type="expense", amount=50.0, tx_date=date(2026, 2, 28))
    _add_transaction(session, household=data["other_household"], account=data["other_account"],
                     category=data["other_cat"], member=data["other_user"],
                     tx_type="expense", amount=9999.0, tx_date=date(2026, 2, 1))
    session.commit()

    response = client.get(
        "/summary/range",
        params={"from": "2026-01-31", "to": "2026-02-28"},
        headers=_auth_headers(data["user"]),
    )

    assert response.status_code == 200
    assert response.json() == {
        "monthly": [
            {"month": "2026-01", "income": 1200.0, "expense": 0.0, "net": 1200.0},
            {"month": "2026-02", "income": 0.0, "expense": 250.0, "net": -250.0},
        ],
        "byCategory": [
            {"categoryId": data["cat_food"].id, "total": 200.0},
            {"categoryId": data["cat_transport"].id, "total": 50.0},
        ],
    }


def test_range_summary_validates_date_order(client, setup_data):
    response = client.get(
        "/summary/range",
        params={"from": "2026-02-01", "to": "2026-01-31"},
        headers=_auth_headers(setup_data["user"]),
    )
    assert response.status_code == 422


def test_report_exports_are_authenticated_and_isolated(client, session, setup_data):
    data = setup_data
    _add_transaction(session, household=data["household"], account=data["account"],
                     category=data["cat_salary"], member=data["user"],
                     tx_type="income", amount=1200.0, tx_date=date(2026, 2, 1))
    _add_transaction(session, household=data["household"], account=data["account"],
                     category=data["cat_food"], member=data["member2"],
                     tx_type="expense", amount=200.0, tx_date=date(2026, 2, 2))
    _add_transaction(session, household=data["other_household"], account=data["other_account"],
                     category=data["other_cat"], member=data["other_user"],
                     tx_type="expense", amount=9999.0, tx_date=date(2026, 2, 2))
    session.commit()

    params = {"format": "csv", "from": "2026-02-01", "to": "2026-02-28"}
    assert client.get("/reports/export", params=params).status_code == 401

    response = client.get("/reports/export", params=params, headers=_auth_headers(data["user"]))
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert 'attachment; filename="reporte-2026-02-01-a-2026-02-28.csv"' == response.headers["content-disposition"]
    content = response.content.decode("utf-8-sig")
    assert "1200.0" in content
    assert "200.0" in content
    assert "9999.0" not in content
    assert "Comida" in content


@pytest.mark.parametrize(
    ("format", "content_type", "signature"),
    [
        ("xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", b"PK\x03\x04"),
        ("docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", b"PK\x03\x04"),
        ("pdf", "application/pdf", b"%PDF"),
    ],
)
def test_report_export_file_formats(client, session, setup_data, format, content_type, signature):
    data = setup_data
    _add_transaction(session, household=data["household"], account=data["account"],
                     category=data["cat_food"], member=data["user"],
                     tx_type="expense", amount=25.0, tx_date=date(2026, 2, 2))
    session.commit()

    response = client.get(
        "/reports/export",
        params={"format": format, "from": "2026-02-01", "to": "2026-02-28"},
        headers=_auth_headers(data["user"]),
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith(content_type)
    assert response.headers["content-disposition"].endswith(f".{format}\"")
    assert response.content.startswith(signature)


def test_report_export_validates_range_and_format(client, setup_data):
    headers = _auth_headers(setup_data["user"])
    assert client.get(
        "/reports/export",
        params={"format": "csv", "from": "2026-02-02", "to": "2026-02-01"},
        headers=headers,
    ).status_code == 422
    assert client.get(
        "/reports/export",
        params={"format": "zip", "from": "2026-02-01", "to": "2026-02-02"},
        headers=headers,
    ).status_code == 422
