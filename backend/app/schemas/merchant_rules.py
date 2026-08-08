from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class _CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class MerchantRuleCreate(_CamelModel):
    pattern: str = Field(min_length=1, max_length=120)
    category_id: str


class MerchantRuleOut(_CamelModel):
    id: str
    household_id: str
    pattern: str
    category_id: str
    category_name: str
    category_type: Literal["expense", "income"]
