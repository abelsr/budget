from datetime import datetime

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class _CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class HouseholdResponse(_CamelModel):
    id: str
    name: str
    currency_code: str


class MemberResponse(_CamelModel):
    id: str
    name: str
    email: str


class InvitationResponse(_CamelModel):
    token: str
    invite_url: str
    expires_at: datetime
