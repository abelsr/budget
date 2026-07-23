from pydantic import BaseModel, ConfigDict, Field, field_validator
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


class UserResponse(_CamelModel):
    id: str
    email: str
    name: str
    household_id: str | None
