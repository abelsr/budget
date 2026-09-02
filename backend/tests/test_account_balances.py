"""Precision of the balance formula (issue #38).

The `Numeric(19, 4)` columns yield `Decimal`, and `balance_sums`/
`account_balance` accumulate in `Decimal` before casting to `float` once at
the end. These tests pin that contract:

- `balance_sums` keeps exact `Decimal` sums per account / cash type.
- `account_balance` sums in `Decimal`, so `0.1 + 0.2 + 0.3` is exact and the
  float result has no binary artifact (a naive float accumulation of
  `0.1 + 0.2` already produces `0.30000000000000004`).
"""

from datetime import date, timedelta
from decimal import Decimal

from app.models import Account, Category, Household, Transaction, User
from app.services.account_balances import account_balance, balance_sums
from app.services.account_access import shared_accounts
from tests.helpers import create_user


def _world(session):
    owner = create_user(session, "balance@example.com", "Balance")
    household = Household(name="Casa Balance", owner_id=owner.id)
    session.add(household)
    session.flush()
    owner.household_id = household.id
    account = Account(household_id=household.id, name="Cash", kind="cash")
    category = Category(
        household_id=household.id, name="Gasto", icon="tag", color="#000000", type="expense"
    )
    session.add_all([account, category])
    session.flush()
    session.add(
        Transaction(
            household_id=household.id,
            account_id=account.id,
            member_id=owner.id,
            type="expense",
            category_id=category.id,
            amount=Decimal("0.1000"),
            date=date.today() - timedelta(days=1),
        )
    )
    session.commit()
    return household, account, category, owner


def test_balance_sums_returns_exact_decimal(session):
    household, account, category, owner = _world(session)
    # A second expense of 0.2000: func.sum must stay 0.3000, not 0.30000000000000004.
    session.add(
        Transaction(
            household_id=household.id,
            account_id=account.id,
            member_id=owner.id,
            type="expense",
            category_id=category.id,
            amount=Decimal("0.2000"),
            date=date.today(),
        )
    )
    session.commit()

    sums = balance_sums(session, household.id, shared_accounts())

    # Exact Decimal per account / type, no float round-trip.
    assert sums[account.id]["expense"] == Decimal("0.3000")
    assert isinstance(sums[account.id]["expense"], Decimal)


def test_account_balance_exact_for_penny_sums(session):
    household, account, category, owner = _world(session)
    session.add(
        Transaction(
            household_id=household.id,
            account_id=account.id,
            member_id=owner.id,
            type="expense",
            category_id=category.id,
            amount=Decimal("0.2000"),
            date=date.today(),
        )
    )
    session.commit()

    sums = balance_sums(session, household.id, shared_accounts())
    # opening_balance 0 - 0.3000 exact; a naive float sum would be 0.30000000000000004.
    balance = account_balance(account.opening_balance, sums.get(account.id, {}))
    assert balance == -0.3
    # The float result has no binary artifact: repr is clean at 2 decimals.
    assert round(balance, 2) == -0.3


def test_account_balance_positive_and_zero(session):
    household, _account, category, owner = _world(session)
    # A fresh account with an opening balance and no ledger entries.
    empty = Account(household_id=household.id, name="Sin movimientos", kind="cash", opening_balance=Decimal("42.0000"))
    session.add(empty)
    session.commit()

    sums = balance_sums(session, household.id, shared_accounts())
    # No rows for this account -> sums empty; balance is just the opening balance.
    assert sums.get(empty.id, {}) == {}
    assert account_balance(empty.opening_balance, sums.get(empty.id, {})) == 42.0
