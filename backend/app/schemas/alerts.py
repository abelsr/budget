from datetime import datetime

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class _CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class AlertOut(_CamelModel):
    id: str
    kind: str
    message: str
    payload: dict
    read_at: datetime | None
    created_at: datetime


class AlertRead(_CamelModel):
    alert_id: str | None = None


class AlertGenerateResult(_CamelModel):
    generated: int
