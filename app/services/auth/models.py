import datetime
import enum
import re

import orjson
from pydantic import BaseModel, ConfigDict, EmailStr, HttpUrl, constr, field_validator, model_validator, Field
from pydantic_extra_types.payment import PaymentCardNumber
from pydantic_extra_types.phone_numbers import PhoneNumber
from tortoise import fields

from app.core import config
from app.core.db import TimeStampMixin
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
    created_at: datetime.datetime


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

    name: constr(strip_whitespace=True, to_lower=True, min_length=3, max_length=20)
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

    @model_validator(mode="after")
    def check_passwords_match(self) -> "UserUpdateAdmin":
        if self.phone and not self.bank:
            raise ValueError("When filling in the phone number, you must also fill in the name of the bank")

        return self


def encoder_google(data):
    if isinstance(data, AdminGoogleToken):
        return data.model_dump_json()
    return orjson.dumps(data)


class User(TimeStampMixin):
    email: str = fields.CharField(unique=True, max_length=100)
    hashed_password: str = fields.TextField()
    is_active: bool = fields.BooleanField(default=True)
    is_superuser: bool = fields.BooleanField(default=False)
    is_verified: bool = fields.BooleanField(default=False)
    name: str = fields.CharField(max_length=20, unique=True)
    telegram: str = fields.CharField(max_length=32, unique=True)
    phone: str | None = fields.TextField(null=True)
    bank: str | None = fields.TextField(null=True)
    bankcard: str | None = fields.TextField(null=True)
    binance_email: str | None = fields.TextField(null=True)
    binance_id: int | None = fields.IntField(null=True)
    discord: str | None = fields.TextField(null=True)
    language: UserLanguage = fields.CharEnumField(UserLanguage, default=UserLanguage.EN)
    google: AdminGoogleToken | None = fields.JSONField(
        null=True, decoder=AdminGoogleToken.model_validate_json, encoder=encoder_google)
    max_orders: int = fields.IntField(default=3)


class AccessToken(TimeStampMixin):
    id: int = fields.BigIntField(pk=True)
    token: str = fields.CharField(unique=True, max_length=100)
    user: fields.ForeignKeyRelation[User] = fields.ForeignKeyField("main.User", to_field="id")


class AccessTokenAPI(TimeStampMixin):
    id: int = fields.BigIntField(pk=True)
    token: str = fields.CharField(unique=True, max_length=100)
    user: fields.ForeignKeyRelation[User] = fields.OneToOneField("main.User", to_field="id")
