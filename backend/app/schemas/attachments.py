from datetime import datetime

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class AttachmentResponse(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel, populate_by_name=True, from_attributes=True
    )

    id: str
    transaction_id: str
    filename: str
    content_type: str
    size_bytes: int
    created_at: datetime
