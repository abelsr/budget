from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class _CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class BudgetCreate(_CamelModel):
    category_id: str
    amount: float = Field(gt=0)


class BudgetUpdate(_CamelModel):
    amount: float = Field(gt=0)


class BudgetOut(_CamelModel):
    id: str
    household_id: str
    category_id: str
    amount: float


class BudgetStatus(_CamelModel):
    category_id: str
    budget: float
    spent: float
    percentage: float
