import datetime
import enum
import re

from fastapi_users_db_beanie import BeanieBaseUserDocument
from fastapi_users_db_beanie.access_token import BeanieBaseAccessTokenDocument

from pydantic import EmailStr, Field, constr, BaseModel, HttpUrl, model_validator, field_validator
from pydantic_core import Url
from pydantic_extra_types.payment import PaymentCardNumber
from pydantic_extra_types.phone_numbers import PhoneNumber
from pymongo import IndexModel
from pymongo.collation import Collation
from beanie import PydanticObjectId
from fastapi_users import schemas

from app.core import config
from app.services.sheets.models import SheetEntity

__all__ = (
    "UserRead",
    "UserCreate",
    "UserUpdate",
    "AdminGoogleToken",
    "UserReadSheets",
    "User",
    "AccessToken",
    "AccessTokenAPI",
)


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


class UserRead(schemas.BaseUser[PydanticObjectId]):
    name: str
    telegram: str
    phone: PhoneNumber | None
    bank: str | None
    bankcard: PaymentCardNumber | None
    binance: EmailStr | None
    discord: str | None
    language: UserLanguage = UserLanguage.EN

    max_orders: int
    created_at: datetime.datetime


class UserReadSheets(schemas.BaseUser[PydanticObjectId], SheetEntity):
    name: str
    telegram: str
    phone: PhoneNumber | None
    bank: str | None
    bankcard: PaymentCardNumber | None
    binance: EmailStr | None
    discord: str | None


class UserCreate(schemas.BaseUserCreate):
    email: EmailStr
    password: str = Field(min_length=6)
    name: constr(strip_whitespace=True, to_lower=True, min_length=3, max_length=20)
    telegram: str
    discord: str

    @field_validator('name', mode="after")
    def username_validate(cls, v: str):
        regex = re.fullmatch(config.app.username_regex, v)
        if not regex:
            raise ValueError("Only Latin, Cyrillic and numbers can be used in the username")
        return v

    @field_validator('discord', mode="after")
    def discord_validate(cls, v: str) -> str:
        if v.startswith("@"):
            if len(v.replace(" ", "")) != len(v):
                raise ValueError("The discord username should be @craaazzzyyfoxx or CraazzzyyFoxx#0001 format")
        elif "#" in v:
            name, dis = v.strip("#")
            if len(dis) != 4:
                raise ValueError("The discord username should be @craaazzzyyfoxx or CraazzzyyFoxx#0001 format")
        else:
            raise ValueError("The discord username should be @craaazzzyyfoxx or CraazzzyyFoxx#0001 format")
        return v


class UserUpdate(schemas.BaseUserUpdate):
    language: UserLanguage | None = None


class UserUpdateAdmin(schemas.BaseUserUpdate):
    phone: PhoneNumber | None = None
    bank: str | None = None
    bankcard: PaymentCardNumber | None = None
    binance: EmailStr | None = None
    max_orders: int

    @model_validator(mode='after')
    def check_passwords_match(self) -> 'UserUpdateAdmin':
        if self.phone and not self.bank:
            raise ValueError("When filling in the phone number, you must also fill in the name of the bank")

        return self


class AccessToken(BeanieBaseAccessTokenDocument):
    pass


class AccessTokenAPI(BeanieBaseAccessTokenDocument):
    class Settings:
        indexes = [IndexModel("user_id", unique=True)]


class User(BeanieBaseUserDocument):
    name: constr(strip_whitespace=True, to_lower=True, min_length=3, max_length=20)
    telegram: str
    phone: PhoneNumber | None = None
    bank: str | None = None
    bankcard: PaymentCardNumber | None = None
    binance: EmailStr | None = None
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
            IndexModel(
                "email", name="case_insensitive_email_index", collation=email_collation
            ),
        ]
        bson_encoders = {
            Url: lambda x: str(x),
            PhoneNumber: lambda x: str(x),
            PaymentCardNumber: lambda x: str(x)
        }
        use_state_management = True
        state_management_save_previous = True

    def serializing_to_sheets(self):
        data = self.model_dump()
        if self.created_at:
            created_at = self.auth_date.strftime("%d.%m.%Y")
            data["created_at"] = created_at
        return data
