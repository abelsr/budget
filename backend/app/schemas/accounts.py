from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel

AccountKind = Literal["cash", "debit", "credit", "savings"]

#: Emisor de la tarjeta (para el widget tipo wallet). "other" = no reconocida.
CardBrand = Literal["visa", "mastercard", "amex", "other"]


class _CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


def _clean_optional(value: str | None) -> str | None:
    """None o cadena vacía → None; si no, texto sin espacios al inicio/fin."""
    if value is None:
        return None
    value = value.strip()
    return value or None


class AccountCreate(_CamelModel):
    name: str = Field(min_length=1, max_length=120)
    kind: AccountKind
    opening_balance: float = 0
    bank: str | None = Field(default=None, max_length=60)
    card_brand: CardBrand | None = None
    last_four: str | None = None
    is_personal: bool = False

    _clean_bank = field_validator("bank")(_clean_optional)

    @field_validator("last_four")
    @classmethod
    def _clean_last_four(cls, value: str | None) -> str | None:
        value = _clean_optional(value)
        if value is None:
            return None
        if len(value) != 4 or not value.isdigit():
            raise ValueError("Los últimos 4 dígitos deben ser un número de 4 cifras")
        return value


class AccountUpdate(_CamelModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    kind: AccountKind | None = None
    opening_balance: float | None = None
    bank: str | None = Field(default=None, max_length=60)
    card_brand: CardBrand | None = None
    last_four: str | None = None
    is_personal: bool | None = None

    _clean_bank = field_validator("bank")(_clean_optional)

    @field_validator("last_four")
    @classmethod
    def _clean_last_four(cls, value: str | None) -> str | None:
        value = _clean_optional(value)
        if value is None:
            return None
        if len(value) != 4 or not value.isdigit():
            raise ValueError("Los últimos 4 dígitos deben ser un número de 4 cifras")
        return value


class AccountOut(_CamelModel):
    id: str
    household_id: str
    name: str
    kind: str
    opening_balance: float
    balance: float
    bank: str | None
    card_brand: str | None
    last_four: str | None
    is_personal: bool
