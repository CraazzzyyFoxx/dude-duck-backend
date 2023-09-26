import typing

from beanie import Indexed, PydanticObjectId
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.db import TimeStampMixin
from app.services.orders import models as order_models
from app.services.orders import schemas as order_schemas

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


class OrderSheetParse(TimeStampMixin):
    spreadsheet: Indexed(str)
    sheet_id: int
    start: int = Field(default=2, gt=1)
    items: list[OrderSheetParseItem]

    is_user: bool

    class Settings:
        name = "order_sheet_parse"
        use_state_management = True
        state_management_save_previous = True
        validate_on_save = True


class OrderSheetParseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: PydanticObjectId
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


class OrderReadSheets(order_schemas.OrderReadSystemBase, SheetEntity):
    booster: str | None = None
    price: order_models.OrderPriceNone
