from datetime import date as date_t
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from app.schemas.attachments import AttachmentResponse
from app.schemas.recurring import Frequency

TransactionType = Literal["expense", "income"]


class _CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class TransactionCreate(_CamelModel):
    client_id: UUID | None = None
    type: TransactionType
    amount: float = Field(gt=0)
    category_id: str
    account_id: str
    date: date_t
    note: str | None = None
    #: Si viene, crea además la regla recurrente y liga esta transacción como su
    #: primera ocurrencia. En la misma operación: partirlo en dos llamadas
    #: dejaría transacciones huérfanas o reglas sin primera ocurrencia.
    repeat: Frequency | None = None


class TransactionUpdate(_CamelModel):
    type: TransactionType | None = None
    amount: float | None = Field(default=None, gt=0)
    category_id: str | None = None
    account_id: str | None = None
    date: date_t | None = None
    note: str | None = None


class TransactionOut(_CamelModel):
    id: str
    household_id: str
    client_id: str | None = None
    type: str
    amount: float
    category_id: str
    account_id: str
    #: Autor inmutable autenticado; conserva el nombre memberId por compatibilidad.
    member_id: str
    #: Nombre del autor histórico, incluso si ya no pertenece al hogar.
    author_name: str
    date: date_t
    note: str | None
    #: Regla que la generó, o NULL si se capturó a mano.
    recurring_rule_id: str | None = None
    attachments: list[AttachmentResponse] = []
