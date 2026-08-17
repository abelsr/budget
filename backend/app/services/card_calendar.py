"""Pure date math for card cycles and MSI instalment schedules.

Shared by the account API, the forecast, and the alerts so the three can
never drift. Dates are derived, never stored.
"""

from datetime import date, timedelta

from app.services.recurring import advance


def _place_day(year: int, month: int, day: int) -> date:
    # statement_day is constrained to 1..28, so no month-length clamp is
    # needed here (unlike anchor days, which may be 29-31).
    return date(year, month, day)


def next_statement_date(statement_day: int, after: date) -> date:
    """First day-`statement_day` occurrence strictly after `after`."""
    candidate = _place_day(after.year, after.month, statement_day)
    if candidate <= after:
        year = candidate.year + 1 if candidate.month == 12 else candidate.year
        month = 1 if candidate.month == 12 else candidate.month + 1
        candidate = _place_day(year, month, statement_day)
    return candidate


def last_statement_date(statement_day: int, before: date) -> date:
    """Last day-`statement_day` occurrence strictly before `before`."""
    candidate = _place_day(before.year, before.month, statement_day)
    if candidate >= before:
        year = candidate.year - 1 if candidate.month == 1 else candidate.year
        month = 12 if candidate.month == 1 else candidate.month - 1
        candidate = _place_day(year, month, statement_day)
    return candidate


def payment_due_date(statement: date, payment_due_days: int) -> date:
    """Payment due date for a statement issued on `statement`."""
    return statement + timedelta(days=payment_due_days)


def instalment_schedule(plan) -> tuple[tuple[date, float], ...]:
    """Derived (due date, amount) pairs for every instalment.

    Walks `advance()` monthly from `first_due_date` keeping the anchor day,
    so Jan 31 -> Feb 28/29 -> Mar 31. The last instalment absorbs the
    rounding remainder so the instalments sum exactly to `total_amount`.
    """
    items: list[tuple[date, float]] = []
    current = plan.first_due_date
    for index in range(plan.months):
        amount = (
            round(float(plan.total_amount) - index * float(plan.monthly_amount), 4)
            if index == plan.months - 1
            else float(plan.monthly_amount)
        )
        items.append((current, amount))
        current = advance(current, "monthly", anchor_day=plan.first_due_date.day)
    return tuple(items)


def next_unpaid_due(plan) -> tuple[date, float] | None:
    """The next (due date, amount) still unpaid, or None when completed."""
    if plan.paid_count >= plan.months:
        return None
    return instalment_schedule(plan)[plan.paid_count]
