from datetime import date as date_t
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from app.schemas.attachments import AttachmentResponse

TransactionType = Literal["expense", "income"]


class _CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class TransactionCreate(_CamelModel):
    type: TransactionType
    amount: float = Field(gt=0)
    category_id: str
    account_id: str
    date: date_t
    note: str | None = None


class TransactionUpdate(_CamelModel):
    type: TransactionType | None = None
    amount: float | None = Field(default=None, gt=0)
    category_id: str | None = None
    account_id: str | None = None
    date: date_t | None = None
    note: str | None = None


class TransactionOut(_CamelModel):
    id: str
    household_id: str
    type: str
    amount: float
    category_id: str
    account_id: str
    member_id: str
    date: date_t
    note: str | None
    attachments: list[AttachmentResponse] = []
