from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

CategoryType = Literal["expense", "income"]

_COLOR_PATTERN = r"^#[0-9a-fA-F]{6}$"


class _CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class CategoryCreate(_CamelModel):
    name: str = Field(min_length=1, max_length=120)
    icon: str = Field(min_length=1, max_length=60)
    color: str = Field(pattern=_COLOR_PATTERN)
    type: CategoryType


class CategoryUpdate(_CamelModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    icon: str | None = Field(default=None, min_length=1, max_length=60)
    color: str | None = Field(default=None, pattern=_COLOR_PATTERN)
    type: CategoryType | None = None
    active: bool | None = None


class CategoryOut(_CamelModel):
    id: str
    household_id: str
    name: str
    icon: str
    color: str
    type: str
    active: bool
