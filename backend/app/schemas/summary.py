from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class _CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class CategoryTotal(_CamelModel):
    category_id: str
    total: float


class MonthSummaryResponse(_CamelModel):
    income: float
    expense: float
    by_category: list[CategoryTotal]


class RangeMonthTotal(_CamelModel):
    month: str
    income: float
    expense: float
    net: float


class RangeSummaryResponse(_CamelModel):
    monthly: list[RangeMonthTotal]
    by_category: list[CategoryTotal]
