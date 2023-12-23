import re
import typing
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints, field_validator
from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core import config, db

__all__ = (
    "UserRead",
    "UserCreate",
    "UserUpdate",
    "UserUpdateAdmin",
    "User",
    "RefreshToken",
    "AccessTokenAPI",
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


class User(db.TimeStampMixin):
    __tablename__ = "user"

    email: Mapped[str] = mapped_column(String(100), unique=True)
    hashed_password: Mapped[str] = mapped_column(Text())
    is_active: Mapped[bool] = mapped_column(default=True)
    is_superuser: Mapped[bool] = mapped_column(default=False)
    is_verified: Mapped[bool] = mapped_column(default=False)
    is_verified_email: Mapped[bool] = mapped_column(default=False)
    name: Mapped[str] = mapped_column(String(20), unique=True)
    max_orders: Mapped[int] = mapped_column(default=3)


class RefreshToken(db.TimeStampMixin):
    __tablename__ = "refresh_token"

    token: Mapped[str] = mapped_column(String(), unique=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"))
    user: Mapped["User"] = relationship()


class AccessTokenAPI(db.TimeStampMixin):
    __tablename__ = "access_token_api"

    token: Mapped[str] = mapped_column(String(100), unique=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"))
    user: Mapped["User"] = relationship()
