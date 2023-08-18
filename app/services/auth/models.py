import datetime
import enum

from fastapi_users_db_beanie import BeanieBaseUserDocument
from fastapi_users_db_beanie.access_token import BeanieBaseAccessTokenDocument

from pydantic import EmailStr, Field, constr, BaseModel, HttpUrl, model_validator
from pydantic_core import Url
from pydantic_extra_types.payment import PaymentCardNumber
from pydantic_extra_types.phone_numbers import PhoneNumber
from pymongo import IndexModel
from pymongo.collation import Collation
from beanie import PydanticObjectId
from fastapi_users import schemas

from app.core import config

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
    name: constr(strip_whitespace=True, to_lower=True, min_length=3, max_length=20, pattern=config.app.username_regex)
    telegram: str
    phone: PhoneNumber | None
    bank: str | None
    bankcard: PaymentCardNumber | None
    binance: EmailStr | None
    discord: str | None
    language: UserLanguage = UserLanguage.EN

    max_orders: int
    created_at: datetime.datetime


class UserReadSheets(schemas.BaseUser[PydanticObjectId]):
    name: str
    telegram: str
    phone: PhoneNumber | None
    bank: str | None
    bankcard: PaymentCardNumber | None
    binance: EmailStr | None
    discord: str | None


class UserCreate(schemas.BaseUserCreate):
    name: constr(strip_whitespace=True, to_lower=True, min_length=3, max_length=20, pattern=config.app.username_regex)
    telegram: str
    phone: PhoneNumber | None = None
    bank: str | None = None
    bankcard: PaymentCardNumber | None = None
    binance: EmailStr | None = None
    discord: str | None = None
    language: UserLanguage = UserLanguage.EN

    @model_validator(mode='after')
    def check_passwords_match(self) -> 'UserCreate':
        if self.phone and not self.bank:
            raise ValueError("When filling in the phone number, you must also fill in the name of the bank")

        return self


class UserUpdate(schemas.BaseUserUpdate):
    language: UserLanguage | None = None
    phone: PhoneNumber | None = None
    bank: str | None = None
    bankcard: PaymentCardNumber | None = None
    binance: EmailStr | None = None

    @model_validator(mode='after')
    def check_passwords_match(self) -> 'UserCreate':
        if self.phone and not self.bank:
            raise ValueError("When filling in the phone number, you must also fill in the name of the bank")

        return self


class AccessToken(BeanieBaseAccessTokenDocument):
    pass


class AccessTokenAPI(BeanieBaseAccessTokenDocument):
    class Settings:
        indexes = [IndexModel("user_id", unique=True)]


class User(BeanieBaseUserDocument):
    name: constr(strip_whitespace=True, to_lower=True, min_length=3, max_length=20, pattern=config.app.username_regex)
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

    def serializing_to_sheets(self):
        data = self.model_dump()
        if self.created_at:
            created_at = self.auth_date.strftime("%d.%m.%Y")
            data["created_at"] = created_at
        return data

