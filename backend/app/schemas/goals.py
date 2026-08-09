from datetime import date
from decimal import Decimal, InvalidOperation

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel


class _CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


MAX_MONEY = Decimal("999999999999999.9999")


def _money(value: object) -> Decimal:
    """Accept JSON numbers/strings that fit PostgreSQL NUMERIC(19, 4) exactly."""
    if isinstance(value, bool):
        raise ValueError("El monto debe ser un número")
    try:
        amount = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError("El monto debe ser un número válido") from exc
    if not amount.is_finite():
        raise ValueError("El monto debe ser finito")
    if amount.as_tuple().exponent < -4:
        raise ValueError("El monto admite hasta 4 decimales")
    if abs(amount) > MAX_MONEY:
        raise ValueError("El monto excede el límite permitido")
    return amount


def _clean_name(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("El nombre es obligatorio")
    return value


class SavingsGoalCreate(_CamelModel):
    name: str = Field(min_length=1, max_length=120)
    target_amount: Decimal = Field(gt=0)
    current_amount: Decimal = Decimal("0")
    target_date: date | None = None
    account_id: str | None = None
    icon: str = Field(default="piggy-bank", min_length=1, max_length=60)
    color: str = Field(default="#30b0c7", pattern=r"^#[0-9a-fA-F]{6}$")
    plan_paused: bool = False

    _strip_name = field_validator("name")(_clean_name)
    _validate_money = field_validator("target_amount", "current_amount", mode="before")(_money)


class SavingsGoalUpdate(_CamelModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    target_amount: Decimal | None = Field(default=None, gt=0)
    target_date: date | None = None
    account_id: str | None = None
    icon: str | None = Field(default=None, min_length=1, max_length=60)
    color: str | None = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")
    archived: bool | None = None
    plan_paused: bool | None = None

    _strip_name = field_validator("name")(_clean_name)

    @field_validator("name", "target_amount", "icon", "color", "archived", "plan_paused", mode="before")
    @classmethod
    def _reject_null_for_non_nullable_fields(cls, value: object) -> object:
        if value is None:
            raise ValueError("Este campo no puede ser nulo")
        return value

    _validate_target_amount = field_validator("target_amount", mode="before")(_money)


class SavingsGoalContribution(_CamelModel):
    amount: Decimal

    _validate_money = field_validator("amount", mode="before")(_money)

    @field_validator("amount")
    @classmethod
    def _nonzero_amount(cls, value: Decimal) -> Decimal:
        if value == 0:
            raise ValueError("El aporte no puede ser cero")
        return value


class SavingsGoalOut(_CamelModel):
    id: str
    household_id: str
    name: str
    target_amount: float
    current_amount: float
    target_date: date | None
    account_id: str | None
    icon: str
    color: str
    archived: bool
    progress_pct: float
    remaining: float
    is_completed: bool
    plan_paused: bool
    plan_status: str
    required_monthly_contribution: float | None
