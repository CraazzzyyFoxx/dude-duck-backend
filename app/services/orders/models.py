import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field
from tortoise import fields

from app.core.db import TimeStampMixin


class OrderStatus(Enum):
    Refund = "Refund"
    InProgress = "In Progress"
    Completed = "Completed"


class OrderPaidStatus(Enum):
    Paid = "Paid"
    NotPaid = "Not Paid"


class OrderInfoMetaRead(BaseModel):
    boost_type: str | None = None
    region_fraction: str | None = None
    server: str | None = None
    category: str | None = None
    character_class: str | None = None
    platform: str | None = None
    game: str | None = None
    purchase: str | None = None
    comment: str | None = None
    eta: str | None = None


class OrderInfoRead(OrderInfoMetaRead):
    boost_type: str
    game: str
    purchase: str


class OrderPriceMeta(BaseModel):
    price_booster_dollar: float | None = None
    price_booster_gold: float | None = None


class OrderPriceNone(OrderPriceMeta):
    price_dollar: float | None = None


class OrderPriceRead(OrderPriceNone):
    price_dollar: float
    price_booster_dollar: float


class OrderCredentialsRead(BaseModel):
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

    info: OrderInfoRead
    price: OrderPriceRead
    credentials: OrderCredentialsRead

    auth_date: datetime.datetime | None = None
    end_date: datetime.datetime | None = None


class OrderUpdate(BaseModel):
    shop: str | None = None
    shop_order_id: str | None = None
    contact: str | None = None

    screenshot: str | None = None

    status: OrderStatus | None = None
    status_paid: OrderPaidStatus | None = None

    info: OrderInfoMetaRead | None = None
    price: OrderPriceNone | None = None
    credentials: OrderCredentialsRead | None = None

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
    auth_date: datetime.datetime | None = fields.DatetimeField(null=True)
    end_date: datetime.datetime | None = fields.DatetimeField(null=True)

    info: fields.ReverseRelation["OrderInfo"] | "OrderInfo"
    price: fields.ReverseRelation["OrderPrice"] | "OrderPrice"
    credentials: fields.ReverseRelation["OrderCredentials"] | "OrderCredentials"


class OrderInfo(TimeStampMixin):
    order: fields.ForeignKeyRelation[Order] = fields.OneToOneField("main.Order", related_name="info")
    boost_type: str = fields.CharField(max_length=10)
    region_fraction: str | None = fields.TextField(null=True)
    server: str | None = fields.TextField(null=True)
    category: str | None = fields.TextField(null=True)
    character_class: str | None = fields.TextField(null=True)
    platform: str | None = fields.CharField(max_length=20, null=True)
    game: str = fields.TextField()
    purchase: str = fields.TextField()
    comment: str | None = fields.TextField(null=True)
    eta: str | None = fields.TextField(null=True)


class OrderPrice(TimeStampMixin):
    order: fields.ForeignKeyRelation[Order] = fields.OneToOneField("main.Order", related_name="price")
    price_dollar: float = fields.FloatField()
    price_booster_dollar: float = fields.FloatField()
    price_booster_gold: float | None = fields.FloatField(null=True)


class OrderCredentials(TimeStampMixin):
    order: fields.ForeignKeyRelation[Order] = fields.OneToOneField("main.Order", related_name="credentials")
    battle_tag: str | None = fields.TextField(null=True)
    nickname: str | None = fields.TextField(null=True)
    login: str | None = fields.TextField(null=True)
    password: str | None = fields.TextField(null=True)
    vpn: str | None = fields.TextField(null=True)
    discord: str | None = fields.TextField(null=True)
