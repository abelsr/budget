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


def _make_user(session: Session, household: Household, email: str, name: str) -> User:
    user = User(
        email=email,
        hashed_password="x",
        name=name,
        household_id=household.id,
    )
    session.add(user)
    session.flush()
    return user


@pytest.fixture(name="setup_data")
def setup_data_fixture(session: Session):
    """Hogar principal con 2 usuarios, cuenta y 2 categorías; y un segundo hogar."""
    household = Household(name="Familia Pérez", currency_code="MXN")
    other_household = Household(name="Otro Hogar", currency_code="USD")
    session.add_all([household, other_household])
    session.flush()

    user = _make_user(session, household, "ana@example.com", "Ana")
    member2 = _make_user(session, household, "luis@example.com", "Luis")
    other_user = _make_user(session, other_household, "otro@example.com", "Otro")

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


def test_get_my_household_members(client, setup_data):
    data = setup_data
    response = client.get("/households/me/members", headers=_auth_headers(data["user"]))
    assert response.status_code == 200
    members = response.json()
    assert len(members) == 2
    emails = {m["email"] for m in members}
    assert emails == {"ana@example.com", "luis@example.com"}
    for m in members:
        assert set(m.keys()) == {"id", "name", "email"}


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
