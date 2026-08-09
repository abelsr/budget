from datetime import date

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel


class _CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class BudgetCreate(_CamelModel):
    category_id: str
    amount: float = Field(gt=0)
    month: date | None = None
    rollover: bool = False

    @field_validator("month")
    @classmethod
    def normalize_month(cls, value: date | None) -> date | None:
        return value.replace(day=1) if value is not None else None


class BudgetUpdate(_CamelModel):
    amount: float = Field(gt=0)
    rollover: bool | None = None


class BudgetOut(_CamelModel):
    id: str
    household_id: str
    category_id: str
    amount: float
    month: date | None
    rollover: bool


class BudgetStatus(_CamelModel):
    category_id: str
    budget: float
    available: float
    spent: float
    percentage: float
