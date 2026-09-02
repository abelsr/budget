from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic.alias_generators import to_camel


class _CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


def _validate_email(value: str) -> str:
    if "@" not in value:
        raise ValueError("El correo debe contener '@'")
    return value


class RegisterRequest(_CamelModel):
    email: str = Field(min_length=3)
    password: str = Field(min_length=8)
    name: str = Field(min_length=1, max_length=120)
    household_name: str = Field(min_length=1, max_length=120)

    _check_email = field_validator("email")(_validate_email)


class LoginRequest(_CamelModel):
    email: str = Field(min_length=3)
    password: str

    _check_email = field_validator("email")(_validate_email)


class JoinRequest(_CamelModel):
    token: str
    email: str = Field(min_length=3)
    password: str = Field(min_length=8)
    name: str = Field(min_length=1, max_length=120)

    _check_email = field_validator("email")(_validate_email)


class TokenResponse(_CamelModel):
    access_token: str
    token_type: str = "bearer"
    #: jti del token emitido; el SPA lo guarda para detectar token obsoleto
    #: sin poder leer el JWT (issue #34, cookie httpOnly).
    token_identifier: str


class RefreshRequest(_CamelModel):
    #: Token a renovar. Opcional con cookie httpOnly (issue #34): si el SPA no
    #: puede leer el JWT (está en una cookie httpOnly), lo toma la app del
    #: cookie `settings.session_cookie_name` en lugar del body.
    access_token: str | None = None


class UserResponse(_CamelModel):
    id: str
    email: str
    name: str
    household_id: str | None
    sex: Literal["female", "male", "non_binary", "prefer_not_to_say"] | None
    birth_date: date | None
    has_avatar: bool
    avatar_updated_at: datetime | None
    #: False → el frontend manda al wizard de `/onboarding`.
    onboarding_completed: bool


class ProfileUpdateRequest(_CamelModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    sex: Literal["female", "male", "non_binary", "prefer_not_to_say"] | None = None
    birth_date: date | None = None

    @model_validator(mode="after")
    def validate_update(self):
        if not self.model_fields_set.intersection({"name", "sex", "birth_date"}):
            raise ValueError("Debes enviar al menos un campo para actualizar")
        if "name" in self.model_fields_set and self.name is None:
            raise ValueError("El nombre no puede ser nulo")
        if self.birth_date is not None:
            today = date.today()
            if self.birth_date > today:
                raise ValueError("La fecha de nacimiento no puede estar en el futuro")
            try:
                oldest_allowed = today.replace(year=today.year - 120)
            except ValueError:
                oldest_allowed = today.replace(year=today.year - 120, day=28)
            if self.birth_date < oldest_allowed:
                raise ValueError("La fecha de nacimiento no puede ser mayor a 120 años")
        return self


class ChangePasswordRequest(_CamelModel):
    current_password: str
    new_password: str = Field(min_length=8)


class OnboardingRequest(_CamelModel):
    completed: bool = True
