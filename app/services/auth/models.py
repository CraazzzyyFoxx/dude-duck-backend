import datetime
import enum
import re

from beanie import PydanticObjectId
from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl, constr, field_validator, model_validator
from pydantic_core import Url
from pydantic_extra_types.payment import PaymentCardNumber
from pydantic_extra_types.phone_numbers import PhoneNumber
from pymongo import IndexModel
from pymongo.collation import Collation

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

    id: PydanticObjectId
    email: EmailStr
    is_active: bool = True
    is_superuser: bool = False
    is_verified: bool = False

    name: str
    telegram: str
    phone: PhoneNumber | None
    bank: str | None
    bankcard: PaymentCardNumber | None
    binance_email: EmailStr | None
    binance_id: int | None
    discord: str | None
    language: UserLanguage = UserLanguage.EN

    max_orders: int
    created_at: datetime.datetime


class UserReadSheets(SheetEntity):
    model_config = ConfigDict(from_attributes=True)

    id: PydanticObjectId
    email: EmailStr
    name: str
    telegram: str
    phone: PhoneNumber | None
    bank: str | None
    bankcard: PaymentCardNumber | None
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

    @field_validator("discord", mode="after")
    def discord_validate(cls, v: str) -> str:
        if v.startswith("@"):
            if len(v.replace(" ", "")) != len(v):
                raise ValueError("The discord username should be @craaazzzyyfoxx or CraazzzyyFoxx#0001 format")
        elif "#" in v:
            name, dis = v.split("#")
            if len(dis) != 4:
                raise ValueError("The discord username should be @craaazzzyyfoxx or CraazzzyyFoxx#0001 format")
        else:
            raise ValueError("The discord username should be @craaazzzyyfoxx or CraazzzyyFoxx#0001 format")
        return v


class BaseUserUpdate(BaseModel):
    password: str | None = None
    email: EmailStr | None = None
    is_active: bool | None = None
    is_superuser: bool | None = None
    is_verified: bool | None = None


class UserUpdate(BaseUserUpdate):
    language: UserLanguage | None = None


class UserUpdateAdmin(BaseUserUpdate):
    phone: PhoneNumber | None = None
    bank: str | None = None
    bankcard: PaymentCardNumber | None = None
    binance_email: EmailStr | None = None
    binance_id: int | None = None
    max_orders: int | None = None
    google: AdminGoogleToken | None = None

    @model_validator(mode="after")
    def check_passwords_match(self) -> "UserUpdateAdmin":
        if self.phone and not self.bank:
            raise ValueError("When filling in the phone number, you must also fill in the name of the bank")

        return self


class AccessToken(TimeStampMixin):
    token: str
    user_id: PydanticObjectId

    class Settings:
        indexes = [IndexModel("token", unique=True)]
        validate_on_save = True


class AccessTokenAPI(TimeStampMixin):
    token: str
    user_id: PydanticObjectId

    class Settings:
        indexes = [IndexModel("user_id", unique=True)]
        validate_on_save = True


class User(TimeStampMixin):
    email: str
    hashed_password: str
    is_active: bool = True
    is_superuser: bool = False
    is_verified: bool = False

    name: constr(strip_whitespace=True, to_lower=True, min_length=3, max_length=20)
    telegram: str
    phone: PhoneNumber | None = None
    bank: str | None = None
    bankcard: PaymentCardNumber | None = None
    binance_email: EmailStr | None = None
    binance_id: int | None = None
    discord: str | None = None
    language: UserLanguage = UserLanguage.EN

    google: AdminGoogleToken | None = None

    max_orders: int = Field(default=3)
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)

    class Settings:
        email_collation = Collation("en", strength=2)
        indexes = [
            IndexModel("email", unique=True),
            IndexModel("name", unique=True),
            IndexModel("email", name="case_insensitive_email_index", collation=email_collation),
        ]
        bson_encoders = {
            Url: lambda x: str(x),
            PhoneNumber: lambda x: str(x),
            PaymentCardNumber: lambda x: str(x),
        }
        use_state_management = True
        state_management_save_previous = True
        validate_on_save = True
