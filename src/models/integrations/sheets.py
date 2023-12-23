import typing

from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl, field_validator
from sqlalchemy import BigInteger, Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core import db
from src.models.auth import User
from src.schemas import OrderReadSystemMeta

__all__ = (
    "SheetEntity",
    "OrderSheetParseItem",
    "OrderSheetParseItemDB",
    "OrderSheetParse",
    "OrderSheetParseRead",
    "OrderSheetParseUpdate",
    "OrderSheetParseCreate",
    "OrderReadSheets",
    "AdminGoogleToken",
    "AdminGoogleTokenDB",
    "GoogleTokenUser",
    "UserReadSheets",
    "allowed_types",
    "CreateUpdateUserSheets",
)


allowed_types = [
    "int",
    "str",
    "timedelta",
    "datetime",
    "SecretStr",
    "EmailStr",
    "HttpUrl",
    "float",
    "PhoneNumber",
    "PaymentCardNumber",
    "bool",
]


class SheetEntity(BaseModel):
    spreadsheet: str
    sheet_id: int
    row_id: int


class OrderSheetParseItem(BaseModel):
    name: str
    row: int
    null: bool = Field(default=False)
    generated: bool = Field(default=False)

    valid_values: list[typing.Any] = Field(examples=[["Completed", "In Progress", "Refund"]])
    type: str = Field(examples=allowed_types)

    @field_validator("type")
    def validate_type(cls, v: str) -> str:
        if "|" in v:
            vs = v.split("|")
        else:
            vs = [v]
        for x in vs:
            if x.strip() not in allowed_types:
                raise ValueError(f"Type can be [{' | '.join(allowed_types)}]")
        return v


class OrderSheetParseItemDB(typing.TypedDict):
    name: str
    row: int
    null: bool
    generated: bool

    valid_values: list[str]
    type: str


class OrderSheetParse(db.TimeStampMixin):
    __tablename__ = "order_sheet_parse"

    spreadsheet: Mapped[str] = mapped_column(String())
    sheet_id: Mapped[int] = mapped_column(BigInteger())
    start: Mapped[int] = mapped_column(BigInteger())
    items: Mapped[list[OrderSheetParseItem]] = mapped_column(JSONB())
    is_user: Mapped[bool] = mapped_column(Boolean(), default=False)

    __table_args__ = (
        # Index("idx_spreadsheet_sheet_id", spreadsheet, sheet_id, unique=True),
        UniqueConstraint(spreadsheet, sheet_id, name="u_spreadsheet_sheet_id"),
    )


class OrderSheetParseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    spreadsheet: str
    sheet_id: int
    start: int
    items: list[OrderSheetParseItem]

    is_user: bool


class OrderSheetParseUpdate(BaseModel):
    start: int = Field(default=2, gt=1)
    items: list[OrderSheetParseItem] = Field(default=[])
    is_user: bool | None = Field(default=None)


class OrderSheetParseCreate(BaseModel):
    spreadsheet: str
    sheet_id: int
    start: int = Field(default=2, gt=1)
    items: list[OrderSheetParseItem]
    is_user: bool = False


class OrderReadSheets(OrderReadSystemMeta, SheetEntity):
    booster: str | None = None
    screenshot: str | None = None


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


class GoogleTokenUser(db.TimeStampMixin):
    __tablename__ = "integration_google_token_user"

    user_id: Mapped[int] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"))
    user: Mapped["User"] = relationship()
    token: Mapped[AdminGoogleTokenDB] = mapped_column(JSONB())


class CreateUpdateUserSheets(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    is_verified: bool
    is_verified_email: bool
    name: str
    max_orders: int
    phone: str | None = None
    bank: str | None = None
    bankcard: str | None = None
    binance_email: EmailStr | None = None
    binance_id: int | None = None
    trc20: str | None = None
    discord: str | None = None
    telegram: str | None = None


class UserReadSheets(SheetEntity, CreateUpdateUserSheets):
    pass
