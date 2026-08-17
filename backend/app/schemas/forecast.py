from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class _CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class ForecastPoint(_CamelModel):
    date: date
    income: float
    expense: float
    delta: float
    balance: float


class ForecastUpcoming(_CamelModel):
    date: date
    #: Effect on the shared household cash.
    type: Literal["income", "expense"]
    amount: float
    label: str
    source: Literal["transaction", "recurring", "card_due", "instalment_due"]


class ForecastResponse(_CamelModel):
    as_of: date
    days: int
    opening_balance: float
    balance: list[ForecastPoint]
    upcoming: list[ForecastUpcoming]
