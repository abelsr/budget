from datetime import date

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class TicketScanResponse(BaseModel):
    """Contrato con el frontend (scan.ts): serializa en camelCase."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    merchant: str
    total: float
    date: date
    suggested_category_id: str
    confidence: float
