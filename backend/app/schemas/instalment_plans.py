import datetime as dt

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class _CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class InstalmentPlanCreate(_CamelModel):
    source_transaction_id: str
    months: int = Field(ge=2, le=48)
    first_due_date: dt.date


class InstalmentPlanPay(_CamelModel):
    #: When set, a cash->card transfer is created for the instalment.
    source_account_id: str | None = None
    date: dt.date | None = None


class InstalmentScheduleItem(_CamelModel):
    date: dt.date
    amount: float
    paid: bool


class InstalmentPlanOut(_CamelModel):
    id: str
    household_id: str
    account_id: str
    account_name: str
    source_transaction_id: str
    months: int
    total_amount: float
    monthly_amount: float
    first_due_date: dt.date
    paid_count: int
    status: str
    next_due_date: dt.date | None
    next_due_amount: float | None
    schedule: list[InstalmentScheduleItem]
    created_at: dt.datetime
