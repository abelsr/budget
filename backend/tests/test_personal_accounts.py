from datetime import date, timedelta

from app.models import Account, Budget, Category, Household, RecurringRule, Transaction
from app.models import SavingsGoal
from tests.helpers import auth_headers as _headers
from tests.helpers import create_user as _user


def test_personal_account_isolation_and_household_aggregates(client, session):
    owner = _user(session, "owner@example.com", "Owner")
    member = _user(session, "member@example.com", "Member")
    household = Household(name="Casa", owner_id=owner.id)
    session.add(household)
    session.flush()
    owner.household_id = household.id
    member.household_id = household.id
    shared = Account(household_id=household.id, name="Casa", kind="cash", opening_balance=100)
    personal = Account(household_id=household.id, owner_id=member.id, name="Privada", kind="cash", opening_balance=50)
    expense = Category(household_id=household.id, name="Comida", icon="x", color="#000000", type="expense")
    session.add_all([shared, personal, expense])
    session.flush()
    session.add_all([
        Transaction(household_id=household.id, type="expense", amount=10, category_id=expense.id, account_id=shared.id, member_id=owner.id, date=date.today()),
        Transaction(household_id=household.id, type="expense", amount=20, category_id=expense.id, account_id=personal.id, member_id=member.id, date=date.today()),
    ])
    session.commit()

    owner_headers, member_headers = _headers(owner), _headers(member)
    assert [row["id"] for row in client.get("/accounts", headers=owner_headers).json()] == [shared.id]
    member_accounts = client.get("/accounts", headers=member_headers).json()
    assert {row["id"] for row in member_accounts} == {shared.id, personal.id}
    assert next(row for row in member_accounts if row["id"] == personal.id)["isPersonal"] is True
    assert {row["accountId"] for row in client.get("/transactions", headers=owner_headers).json()} == {shared.id}
    assert client.get("/summary/month", headers=member_headers).json()["expense"] == 10.0
    assert client.get("/budgets/status", headers=member_headers).json() == []
    report = client.get("/reports/export", params={"format": "csv", "from": date.today(), "to": date.today()}, headers=owner_headers)
    assert report.status_code == 200
    assert "Privada" not in report.content.decode("utf-8-sig")

    payload = {"type": "expense", "amount": 5, "categoryId": expense.id, "accountId": personal.id, "date": date.today().isoformat()}
    assert client.post("/transactions", json=payload, headers=owner_headers).status_code == 404
    assert client.patch(f"/transactions/{session.query(Transaction).filter_by(account_id=personal.id).one().id}", json={"note": "x"}, headers=owner_headers).status_code == 404
    assert client.delete(f"/accounts/{personal.id}", headers=owner_headers).status_code == 404


def test_personal_conversion_rules_recurring_and_member_removal(client, session):
    owner = _user(session, "owner2@example.com", "Owner")
    member = _user(session, "member2@example.com", "Member")
    household = Household(name="Casa", owner_id=owner.id)
    session.add(household)
    session.flush()
    owner.household_id = household.id
    member.household_id = household.id
    shared = Account(household_id=household.id, name="Compartida", kind="cash")
    personal = Account(household_id=household.id, owner_id=member.id, name="Privada", kind="cash")
    category = Category(household_id=household.id, name="Casa", icon="x", color="#000000", type="expense")
    session.add_all([shared, personal, category])
    session.flush()
    rule = RecurringRule(household_id=household.id, type="expense", amount=3, category_id=category.id, account_id=personal.id, created_by_id=member.id, frequency="weekly", next_run_date=date.today() - timedelta(days=7), anchor_day=None)
    session.add(rule)
    session.commit()

    owner_headers, member_headers = _headers(owner), _headers(member)
    assert client.get("/transactions", headers=owner_headers).json() == []
    assert session.query(Transaction).count() == 0
    assert len(client.get("/transactions", headers=member_headers).json()) == 2
    assert client.patch(f"/accounts/{shared.id}", json={"isPersonal": True}, headers=member_headers).status_code == 403
    session.add(SavingsGoal(household_id=household.id, name="Meta", target_amount=10, account_id=shared.id))
    session.commit()
    assert client.patch(f"/accounts/{shared.id}", json={"isPersonal": True}, headers=owner_headers).status_code == 409
    session.query(SavingsGoal).delete()
    session.commit()
    assert client.patch(f"/accounts/{shared.id}", json={"isPersonal": True}, headers=owner_headers).status_code == 200
    assert client.patch(f"/accounts/{shared.id}", json={"isPersonal": False}, headers=member_headers).status_code == 404
    assert client.patch(f"/accounts/{shared.id}", json={"isPersonal": False}, headers=owner_headers).status_code == 200
    assert client.delete(f"/households/me/members/{member.id}", headers=owner_headers).status_code == 409


def test_peer_category_delete_does_not_disclose_personal_transaction_use(client, session):
    owner = _user(session, "category-owner@example.com", "Owner")
    member = _user(session, "category-member@example.com", "Member")
    household = Household(name="Casa", owner_id=owner.id)
    session.add(household)
    session.flush()
    owner.household_id = household.id
    member.household_id = household.id
    personal = Account(household_id=household.id, owner_id=member.id, name="Privada", kind="cash")
    private_category = Category(household_id=household.id, name="Privada", icon="x", color="#000000", type="expense")
    rule_only_category = Category(household_id=household.id, name="Solo regla", icon="x", color="#000000", type="expense")
    unused_category = Category(household_id=household.id, name="Sin uso", icon="x", color="#000000", type="expense")
    session.add_all([personal, private_category, rule_only_category, unused_category])
    session.flush()
    private_budget = Budget(household_id=household.id, category_id=private_category.id, amount=100)
    unused_budget = Budget(household_id=household.id, category_id=unused_category.id, amount=100)
    transaction = Transaction(household_id=household.id, type="expense", amount=10, category_id=private_category.id, account_id=personal.id, member_id=member.id, date=date.today())
    private_rule = RecurringRule(household_id=household.id, type="expense", amount=10, category_id=private_category.id, account_id=personal.id, created_by_id=member.id, frequency="monthly", next_run_date=date.today() + timedelta(days=1), anchor_day=None)
    rule_only = RecurringRule(household_id=household.id, type="expense", amount=10, category_id=rule_only_category.id, account_id=personal.id, created_by_id=member.id, frequency="monthly", next_run_date=date.today() + timedelta(days=1), anchor_day=None)
    session.add_all([private_budget, unused_budget, transaction, private_rule, rule_only])
    session.commit()

    owner_headers = _headers(owner)
    # A private transaction has the same deletion result as an unused category.
    assert client.delete(f"/categories/{private_category.id}", headers=owner_headers).status_code == 204
    assert client.delete(f"/categories/{rule_only_category.id}", headers=owner_headers).status_code == 204
    assert client.delete(f"/categories/{unused_category.id}", headers=owner_headers).status_code == 204
    assert private_category.id not in {row["id"] for row in client.get("/categories", headers=owner_headers).json()}
    assert client.patch(f"/categories/{private_category.id}", json={"name": "X"}, headers=owner_headers).status_code == 404
    remaining_budget_ids = {row["id"] for row in client.get("/budgets", headers=owner_headers).json()}
    assert private_budget.id not in remaining_budget_ids
    assert unused_budget.id not in remaining_budget_ids
    session.refresh(private_category)
    assert private_category.deleted is True
    assert session.get(Transaction, transaction.id) is not None
    session.refresh(private_rule)
    assert private_rule.active is False
    assert client.patch(f"/recurring-rules/{private_rule.id}", json={"active": True}, headers=_headers(member)).status_code == 409
    session.refresh(rule_only_category)
    session.refresh(rule_only)
    assert rule_only_category.deleted is True
    assert rule_only.active is False
    assert session.get(Category, unused_category.id) is None


def test_account_rule_dependencies_block_delete_and_shared_to_personal_conversion(client, session):
    owner = _user(session, "rule-owner@example.com", "Owner")
    member = _user(session, "rule-member@example.com", "Member")
    household = Household(name="Casa", owner_id=owner.id)
    session.add(household)
    session.flush()
    owner.household_id = household.id
    member.household_id = household.id
    shared = Account(household_id=household.id, name="Compartida", kind="cash")
    personal = Account(household_id=household.id, owner_id=member.id, name="Privada", kind="cash")
    category = Category(household_id=household.id, name="Casa", icon="x", color="#000000", type="expense")
    session.add_all([shared, personal, category])
    session.flush()
    shared_rule = RecurringRule(household_id=household.id, type="expense", amount=10, category_id=category.id, account_id=shared.id, created_by_id=member.id, frequency="monthly", next_run_date=date.today() + timedelta(days=1), anchor_day=None)
    personal_rule = RecurringRule(household_id=household.id, type="expense", amount=10, category_id=category.id, account_id=personal.id, created_by_id=member.id, frequency="monthly", next_run_date=date.today() + timedelta(days=1), anchor_day=None)
    session.add_all([shared_rule, personal_rule])
    session.commit()

    owner_headers, member_headers = _headers(owner), _headers(member)
    assert client.delete(f"/categories/{category.id}", headers=owner_headers).status_code == 409
    response = client.patch(f"/accounts/{shared.id}", json={"isPersonal": True}, headers=owner_headers)
    assert response.status_code == 409
    assert response.json()["detail"] == "La cuenta tiene reglas recurrentes de otras personas"
    response = client.delete(f"/accounts/{personal.id}", headers=member_headers)
    assert response.status_code == 409
    assert response.json()["detail"] == "La cuenta tiene reglas recurrentes"
