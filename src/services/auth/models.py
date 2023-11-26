import enum
import re
import typing
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl, StringConstraints, field_validator
from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core import config, db
from src.services.integrations.sheets.models import SheetEntity


class UserLanguage(str, enum.Enum):
    RU = "ru"
    EN = "en"


class AdminGoogleToken(BaseModel):
    type: str
    project_id: str
    private_key_id: str
    private_key: str
    client_email: str
    client_id: str
    auth_uri: HttpUrl
    token_uri: HttpUrl
    auth_provider_x509_cert_url: HttpUrl
    client_x509_cert_url: HttpUrl
    universe_domain: str


class AdminGoogleTokenDB(typing.TypedDict):
    type: str
    project_id: str
    private_key_id: str
    private_key: str
    client_email: str
    client_id: str
    auth_uri: str
    token_uri: str
    auth_provider_x509_cert_url: str
    client_x509_cert_url: str
    universe_domain: str


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    is_active: bool
    is_superuser: bool
    is_verified: bool

    name: str
    telegram: str
    discord: str | None
    language: UserLanguage = UserLanguage.EN

    max_orders: int
    created_at: datetime


class UserReadSheets(SheetEntity):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    name: str
    telegram: str
    phone: str | None
    bank: str | None
    bankcard: str | None
    binance_email: EmailStr | None
    binance_id: int | None
    discord: str | None


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    is_active: bool | None = True
    is_superuser: bool | None = False
    is_verified: bool | None = False

    name: typing.Annotated[str, StringConstraints(strip_whitespace=True, to_lower=True, min_length=3, max_length=20)]
    telegram: str
    discord: str

    @field_validator("name", mode="after")
    def username_validate(cls, v: str):
        regex = re.fullmatch(config.app.username_regex, v)
        if not regex:
            raise ValueError("Only Latin, Cyrillic and numbers can be used in the username")
        return v

    @field_validator("discord")
    def discord_validate(cls, v: str) -> str:
        if "#" in v:
            name, dis = v.split("#")
            if len(dis) == 4:
                return v
        if len(v.replace(" ", "")) == len(v):
            return v
        raise ValueError("The discord username should be craaazzzyyfoxx or CraazzzyyFoxx#0001 format")


class BaseUserUpdate(BaseModel):
    password: str | None = Field(default=None)
    email: EmailStr | None = Field(default=None)


class UserUpdate(BaseUserUpdate):
    language: UserLanguage | None = Field(default=None)


class UserUpdateAdmin(BaseUserUpdate):
    is_active: bool | None = Field(default=None)
    is_superuser: bool | None = Field(default=None)
    is_verified: bool | None = Field(default=None)

    max_orders: int | None = Field(default=None)
    google: AdminGoogleToken | None = Field(default=None)
    telegram: str | None = Field(default=None)
    discord: str | None = Field(default=None)


class User(db.TimeStampMixin):
    __tablename__ = "user"

    email: Mapped[str] = mapped_column(String(100), unique=True)
    hashed_password: Mapped[str] = mapped_column(Text())
    is_active: Mapped[bool] = mapped_column(default=True)
    is_superuser: Mapped[bool] = mapped_column(default=True)
    is_verified: Mapped[bool] = mapped_column(default=True)
    name: Mapped[str] = mapped_column(String(20), unique=True)
    telegram: Mapped[str] = mapped_column(String(32), unique=True)
    discord: Mapped[str | None] = mapped_column(Text(), nullable=True)
    language: Mapped[UserLanguage] = mapped_column(default=UserLanguage.EN)
    google: Mapped[AdminGoogleTokenDB | None] = mapped_column(JSONB(), nullable=True)
    max_orders: Mapped[int] = mapped_column(default=3)


class RefreshToken(db.TimeStampMixin):
    __tablename__ = "refresh_token"

    token: Mapped[str] = mapped_column(String(), unique=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    user: Mapped["User"] = relationship()


class AccessTokenAPI(db.TimeStampMixin):
    __tablename__ = "access_token_api"

    token: Mapped[str] = mapped_column(String(100), unique=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    user: Mapped["User"] = relationship()
