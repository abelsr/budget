from datetime import date as date_t
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

Frequency = Literal["weekly", "monthly"]
TransactionType = Literal["expense", "income"]


class _CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class RecurringRuleCreate(_CamelModel):
    type: TransactionType
    amount: float = Field(gt=0)
    category_id: str
    account_id: str
    frequency: Frequency
    #: Cuándo toca la próxima vez. En el pasado es válido: la primera lectura
    #: materializa el atraso (con un tope, ver `MAX_BACKFILL_DAYS`).
    next_run_date: date_t
    note: str | None = None


class RecurringRuleUpdate(_CamelModel):
    """Solo lo que tiene sentido cambiar sin reescribir la historia. Cambiar
    categoría, cuenta o frecuencia es otra regla: mejor borrar y crear."""

    amount: float | None = Field(default=None, gt=0)
    note: str | None = None
    active: bool | None = None


class RecurringRuleOut(_CamelModel):
    id: str
    household_id: str
    type: str
    amount: float
    category_id: str
    account_id: str
    created_by_id: str
    frequency: str
    next_run_date: date_t
    note: str | None
    active: bool
