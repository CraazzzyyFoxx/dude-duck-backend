import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field
from pydantic_core import Url
from pymongo import IndexModel
from tortoise import fields

from app.core.db import TimeStampMixin


class OrderStatus(Enum):
    Refund = "Refund"
    InProgress = "In Progress"
    Completed = "Completed"


class OrderPaidStatus(Enum):
    Paid = "Paid"
    NotPaid = "Not Paid"


class OrderInfo(BaseModel):
    boost_type: str
    region_fraction: str | None = None
    server: str | None = None
    category: str | None = None
    character_class: str | None = None
    platform: str | None = None
    game: str
    purchase: str
    comment: str | None = None
    eta: str | None = None


class OrderPriceNone(BaseModel):
    price_dollar: float | None = None
    price_booster_dollar: float | None = None
    price_booster_gold: float | None = None


class OrderPrice(OrderPriceNone):
    price_dollar: float
    price_booster_dollar: float


class OrderCredentials(BaseModel):
    battle_tag: str | None = None
    nickname: str | None = None
    login: str | None = None
    password: str | None = None
    vpn: str | None = None
    discord: str | None = None


class OrderCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    order_id: str
    spreadsheet: str
    sheet_id: int
    row_id: int

    date: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    shop: str | None = None
    shop_order_id: str | int | None = None
    contact: str | None = None

    screenshot: str | None = None

    status: OrderStatus
    status_paid: OrderPaidStatus

    info: OrderInfo
    price: OrderPrice
    credentials: OrderCredentials

    auth_date: datetime.datetime | None = None
    end_date: datetime.datetime | None = None


class OrderUpdate(BaseModel):
    shop: str | None = None
    shop_order_id: str | int | None = None
    contact: str | None = None

    screenshot: str | None = None

    status: OrderStatus | None = None
    status_paid: OrderPaidStatus | None = None

    info: OrderInfo | None = None
    price: OrderPrice | None = None
    credentials: OrderCredentials | None = None

    auth_date: datetime.datetime | None = None
    end_date: datetime.datetime | None = None


class Order(TimeStampMixin):
    order_id: str = fields.CharField(max_length=10, unique=True)
    spreadsheet: str = fields.TextField()
    sheet_id: int = fields.BigIntField()
    row_id: int = fields.BigIntField()

    date: datetime.datetime = fields.DatetimeField()
    shop: str | None = fields.TextField(null=True)
    shop_order_id: str | None = fields.TextField(null=True)
    contact: str | None = fields.TextField(null=True)

    screenshot: str | None = fields.TextField(null=True)

    status: OrderStatus = fields.CharEnumField(OrderStatus)
    status_paid: OrderPaidStatus = fields.CharEnumField(OrderPaidStatus)

    info: OrderInfo = fields.JSONField(
        null=True, decoder=OrderInfo.model_validate_json, encoder=lambda x: OrderInfo.model_dump_json(x)
    )
    price: OrderPrice = fields.JSONField(
        null=True, decoder=OrderPrice.model_validate_json, encoder=lambda x: OrderPrice.model_dump_json(x)
    )
    credentials: OrderCredentials = fields.JSONField(
        null=True,
        decoder=OrderCredentials.model_validate_json,
        encoder=lambda x: OrderCredentials.model_dump_json(x),
    )

    auth_date: datetime.datetime | None = fields.DatetimeField(null=True)
    end_date: datetime.datetime | None = fields.DatetimeField(null=True)

    def __hash__(self) -> int:
        return hash(self.id)
