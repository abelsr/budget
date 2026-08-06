from datetime import date as date_t
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from app.schemas.attachments import AttachmentResponse
from app.schemas.recurring import Frequency

TransactionType = Literal["expense", "income", "transfer"]


class _CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class TransactionCreate(_CamelModel):
    client_id: UUID | None = None
    type: TransactionType
    amount: float = Field(gt=0)
    category_id: str | None = None
    account_id: str | None = None
    source_account_id: str | None = None
    destination_account_id: str | None = None
    date: date_t
    note: str | None = None
    #: Si viene, crea además la regla recurrente y liga esta transacción como su
    #: primera ocurrencia. En la misma operación: partirlo en dos llamadas
    #: dejaría transacciones huérfanas o reglas sin primera ocurrencia.
    repeat: Frequency | None = None

    @model_validator(mode="after")
    def validate_shape(self):
        if self.type == "transfer":
            if self.category_id is not None or self.account_id is not None:
                raise ValueError("Una transferencia no usa categoría ni cuenta única")
            if not self.source_account_id or not self.destination_account_id:
                raise ValueError("Una transferencia requiere cuenta origen y destino")
            if self.source_account_id == self.destination_account_id:
                raise ValueError("La cuenta origen y destino deben ser distintas")
            if self.repeat is not None:
                raise ValueError("Las transferencias no pueden ser recurrentes")
        elif not self.category_id or not self.account_id:
            raise ValueError("El movimiento requiere categoría y cuenta")
        return self


class TransactionUpdate(_CamelModel):
    type: TransactionType | None = None
    amount: float | None = Field(default=None, gt=0)
    category_id: str | None = None
    account_id: str | None = None
    date: date_t | None = None
    note: str | None = None
    source_account_id: str | None = None
    destination_account_id: str | None = None


class TransactionOut(_CamelModel):
    id: str
    household_id: str
    client_id: str | None = None
    type: str
    amount: float
    category_id: str | None
    account_id: str
    #: Autor inmutable autenticado; conserva el nombre memberId por compatibilidad.
    member_id: str
    #: Nombre del autor histórico, incluso si ya no pertenece al hogar.
    author_name: str
    date: date_t
    note: str | None
    #: Regla que la generó, o NULL si se capturó a mano.
    recurring_rule_id: str | None = None
    transfer_group_id: str | None = None
    transfer_direction: Literal["outflow", "inflow"] | None = None
    counterparty_account_id: str | None = None
    counterparty_account_name: str | None = None
    attachments: list[AttachmentResponse] = []
