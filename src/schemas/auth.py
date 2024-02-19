import re
import typing
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints, field_validator

from src.core import config

__all__ = (
    "UserRead",
    "UserCreate",
    "UserUpdate",
    "UserUpdateAdmin",

    "BaseUserUpdate",
)

class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    is_active: bool
    is_superuser: bool
    is_verified: bool
    is_verified_email: bool

    name: str

    max_orders: int
    created_at: datetime


class UserCreate(BaseModel):
    email: EmailStr
    password: str

    name: typing.Annotated[
        str,
        StringConstraints(strip_whitespace=True, to_lower=True, min_length=3, max_length=20),
    ]

    @field_validator("name", mode="after")
    def username_validate(cls, v: str):
        regex = re.fullmatch(config.app.username_regex, v)
        if not regex:
            raise ValueError("Only Latin, Cyrillic and numbers can be used in the username")
        return v


class BaseUserUpdate(BaseModel):
    password: str | None = Field(default=None)
    email: EmailStr | None = Field(default=None)


class UserUpdate(BaseUserUpdate):
    pass


class UserUpdateAdmin(BaseUserUpdate):
    is_active: bool | None = Field(default=None)
    is_superuser: bool | None = Field(default=None)
    is_verified: bool | None = Field(default=None)
    is_verified_email: bool | None = Field(default=None)

    max_orders: int | None = Field(default=None)
