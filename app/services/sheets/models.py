import typing

from orjson import orjson
from pydantic import BaseModel, ConfigDict, Field, field_validator
from tortoise import fields

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


def decode(data: str) -> list[OrderSheetParseItem]:
    return [OrderSheetParseItem.model_validate(d) for d in orjson.loads(data)]


def encode(data: list[OrderSheetParseItem]) -> str:
    return str(orjson.dumps([d.model_dump() for d in data]))


class OrderSheetParse(TimeStampMixin):
    spreadsheet: str = fields.TextField()  # noqa
    sheet_id: int = fields.BigIntField()  # noqa
    start: int = fields.IntField(default=2)  # noqa
    items: list[OrderSheetParseItem] = fields.JSONField(decoder=decode)  # noqa
    is_user: bool = fields.BooleanField(default=False)  # noqa

    class Meta:
        unique_together = ("spreadsheet", "sheet_id")


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


class OrderReadSheets(order_schemas.OrderReadSystemBase, SheetEntity):
    booster: str | None = None
    price: order_models.OrderPriceNone
