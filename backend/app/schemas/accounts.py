from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

AccountKind = Literal["cash", "debit", "credit", "savings"]


class _CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class AccountCreate(_CamelModel):
    name: str = Field(min_length=1, max_length=120)
    kind: AccountKind
    opening_balance: float = 0


class AccountUpdate(_CamelModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    kind: AccountKind | None = None
    opening_balance: float | None = None


class AccountOut(_CamelModel):
    id: str
    household_id: str
    name: str
    kind: str
    opening_balance: float
    balance: float
