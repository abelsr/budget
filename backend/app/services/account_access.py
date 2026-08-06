from sqlalchemy import or_

from app.models import Account


def visible_accounts(user_id: str):
    """SQL predicate for shared accounts plus the caller's own personal ones."""
    return or_(Account.owner_id.is_(None), Account.owner_id == user_id)


def shared_accounts():
    """SQL predicate for household-wide calculations and links."""
    return Account.owner_id.is_(None)


def can_operate(account: Account, user_id: str) -> bool:
    return account.owner_id is None or account.owner_id == user_id
