from datetime import date

from app.services.card_calendar import (
    instalment_schedule,
    last_statement_date,
    next_statement_date,
    payment_due_date,
)


class _Plan:
    """Minimal stand-in: the schedule helpers take only these attributes."""

    def __init__(self, first_due_date, months, monthly_amount, total_amount, paid_count=0, status="active"):
        self.first_due_date = first_due_date
        self.months = months
        self.monthly_amount = monthly_amount
        self.total_amount = total_amount
        self.paid_count = paid_count
        self.status = status


def test_next_statement_date_strictly_after():
    assert next_statement_date(15, date(2026, 8, 15)) == date(2026, 9, 15)
    assert next_statement_date(15, date(2026, 8, 16)) == date(2026, 9, 15)
    assert next_statement_date(15, date(2026, 8, 14)) == date(2026, 8, 15)


def test_last_statement_date_strictly_before():
    assert last_statement_date(15, date(2026, 8, 15)) == date(2026, 7, 15)
    assert last_statement_date(15, date(2026, 8, 16)) == date(2026, 8, 15)


def test_statement_day_crosses_year():
    assert next_statement_date(28, date(2026, 12, 31)) == date(2027, 1, 28)
    assert last_statement_date(1, date(2026, 1, 1)) == date(2025, 12, 1)


def test_payment_due_crosses_month():
    assert payment_due_date(date(2026, 8, 15), 20) == date(2026, 9, 4)
    assert payment_due_date(date(2026, 12, 15), 20) == date(2027, 1, 4)


def test_schedule_anchor_day_crosses_february():
    plan = _Plan(date(2027, 1, 31), 3, 100.0, 300.0)
    dates = [d for d, _ in instalment_schedule(plan)]
    assert dates == [date(2027, 1, 31), date(2027, 2, 28), date(2027, 3, 31)]


def test_schedule_anchor_day_leap_year():
    plan = _Plan(date(2028, 1, 31), 3, 100.0, 300.0)
    dates = [d for d, _ in instalment_schedule(plan)]
    assert dates == [date(2028, 1, 31), date(2028, 2, 29), date(2028, 3, 31)]


def test_schedule_last_installment_absorbs_rounding():
    plan = _Plan(date(2026, 9, 10), 6, 850.1667, 5101.0)
    schedule = instalment_schedule(plan)
    assert len(schedule) == 6
    assert [round(a, 4) for _, a in schedule[:5]] == [850.1667] * 5
    assert round(schedule[5][1], 4) == round(5101.0 - 5 * 850.1667, 4)  # 850.1665
    assert round(sum(a for _, a in schedule), 4) == 5101.0
