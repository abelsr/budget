from datetime import datetime

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class _CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class HouseholdResponse(_CamelModel):
    id: str
    name: str
    currency_code: str
    is_owner: bool


class MemberResponse(_CamelModel):
    id: str
    name: str
    email: str
    is_owner: bool


class InvitationResponse(_CamelModel):
    token: str
    invite_url: str
    expires_at: datetime


class ActiveInvitationResponse(_CamelModel):
    id: str
    expires_at: datetime
    created_at: datetime
