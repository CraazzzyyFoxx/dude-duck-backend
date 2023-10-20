import enum
import re

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl, constr, field_validator, model_validator
from pydantic_extra_types.payment import PaymentCardNumber
from pydantic_extra_types.phone_numbers import PhoneNumber
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import BigInteger, String, Text, JSON, ForeignKey

from app.core import config, db
from app.services.sheets.models import SheetEntity


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


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    is_active: bool = True
    is_superuser: bool = False
    is_verified: bool = False

    name: str
    telegram: str
    phone: str | None
    bank: str | None
    bankcard: str | None
    binance_email: EmailStr | None
    binance_id: int | None
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

    name: constr(strip_whitespace=True, to_lower=True, min_length=3, max_length=20)  # noqa
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
    is_active: bool | None = Field(default=None)
    is_superuser: bool | None = Field(default=None)
    is_verified: bool | None = Field(default=None)


class UserUpdate(BaseUserUpdate):
    language: UserLanguage | None = Field(default=None)


class UserUpdateAdmin(BaseUserUpdate):
    phone: PhoneNumber | None = Field(default=None)
    bank: str | None = Field(default=None)
    bankcard: PaymentCardNumber | None = Field(default=None)
    binance_email: EmailStr | None = Field(default=None)
    binance_id: int | None = Field(default=None)
    max_orders: int | None = Field(default=None)
    google: AdminGoogleToken | None = Field(default=None)
    telegram: str | None = Field(default=None)
    discord: str | None = Field(default=None)

    @model_validator(mode="after")
    def check_passwords_match(self) -> "UserUpdateAdmin":
        if self.phone and not self.bank:
            raise ValueError("When filling in the phone number, you must also fill in the name of the bank")

        return self


class User(db.TimeStampMixin):
    __tablename__ = "user"

    _cache_google: AdminGoogleToken | None = None

    email: Mapped[str] = mapped_column(String(100), unique=True)
    hashed_password: Mapped[str] = mapped_column(Text())
    is_active: Mapped[bool] = mapped_column(default=True)
    is_superuser: Mapped[bool] = mapped_column(default=True)
    is_verified: Mapped[bool] = mapped_column(default=True)
    name: Mapped[str] = mapped_column(String(20), unique=True)
    telegram: Mapped[str] = mapped_column(String(32), unique=True)
    phone: Mapped[str | None] = mapped_column(Text(), nullable=True)
    bank: Mapped[str | None] = mapped_column(Text(), nullable=True)
    bankcard: Mapped[str | None] = mapped_column(Text(), nullable=True)
    binance_email: Mapped[str | None] = mapped_column(Text(), nullable=True)
    binance_id: Mapped[int | None] = mapped_column(BigInteger(), nullable=True)
    discord: Mapped[str | None] = mapped_column(Text(), nullable=True)
    language: Mapped[UserLanguage] = mapped_column(default=UserLanguage.EN)
    google_token: Mapped[dict] = mapped_column(JSON(), nullable=True)
    max_orders: Mapped[int] = mapped_column(default=3)

    @property
    def google(self):
        if self._cache_google is None:
            token = AdminGoogleToken.model_validate(self.google_token)
            self._cache_google = token
            return token
        return self._cache_google


class AccessToken(db.TimeStampMixin):
    __tablename__ = "access_token"

    token: Mapped[str] = mapped_column(String(100), unique=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    user: Mapped["User"] = relationship()


class AccessTokenAPI(db.TimeStampMixin):
    __tablename__ = "access_token_api"

    token: Mapped[str] = mapped_column(String(100), unique=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    user: Mapped["User"] = relationship()
