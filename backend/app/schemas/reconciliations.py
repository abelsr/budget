from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class _CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class ReconciliationCreate(_CamelModel):
    statement_date: date
    statement_balance: float


class ReconciliationToggle(_CamelModel):
    reconciled: bool


class ReconciliationTransactionOut(_CamelModel):
    id: str
    type: str
    amount: float
    date: date
    note: str | None
    reconciliation_status: Literal["pending", "reconciled"]


class ReconciliationSessionOut(_CamelModel):
    id: str
    account_id: str
    statement_date: date
    statement_balance: float
    status: Literal["open", "completed", "stale"]
    completed_at: datetime | None
    created_at: datetime


class ReconciliationSessionDetail(ReconciliationSessionOut):
    pending_total: float
    reconciled_total: float
    reconciled_balance: float
    difference: float
    transactions: list[ReconciliationTransactionOut]
