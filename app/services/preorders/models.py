import datetime

from pydantic import BaseModel, ConfigDict, Field
from tortoise import fields

from app.core.db import TimeStampMixin
from app.services.orders import models as order_models
from app.services.sheets import models as sheets_models


class PreOrderPriceUser(BaseModel):
    price_booster_dollar: float | None = Field(default=...)
    price_booster_rub: float | None = Field(default=...)
    price_booster_gold: float | None = Field(default=...)


class PreOrderPriceSystem(BaseModel):
    price_dollar: float | None = Field(default=...)
    price_booster_dollar_without_fee: float | None = Field(default=...)

    price_booster_dollar: float | None = Field(default=...)
    price_booster_rub: float | None = Field(default=...)
    price_booster_gold: float | None = Field(default=...)


class PreOrderCreate(sheets_models.SheetEntity):
    date: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    order_id: str

    info: order_models.OrderInfoRead
    price: PreOrderPriceUser


class PreOrderUpdate(BaseModel):
    info: order_models.OrderInfoRead | None = Field(default=...)
    price: PreOrderPriceUser | None = Field(default=...)
    has_response: bool | None = Field(default=...)


class PreOrder(TimeStampMixin):
    order_id: str = fields.CharField(max_length=10, unique=True)
    spreadsheet: str = fields.TextField()
    sheet_id: int = fields.BigIntField()
    row_id: int = fields.BigIntField()
    date: datetime.datetime = fields.DatetimeField()

    info: fields.ReverseRelation["PreOrderInfo"] | "PreOrderInfo"
    price: fields.ReverseRelation["PreOrderPrice"] | "PreOrderPrice"

    has_response: bool = fields.BooleanField(default=False)


class PreOrderInfo(TimeStampMixin):
    order: fields.ForeignKeyRelation[PreOrder] = fields.OneToOneField("main.PreOrder", related_name="info")
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


class PreOrderPrice(TimeStampMixin):
    order: fields.ForeignKeyRelation[PreOrder] = fields.OneToOneField("main.PreOrder", related_name="price")
    price_dollar: float = fields.FloatField()
    price_booster_dollar: float = fields.FloatField()
    price_booster_gold: float | None = fields.FloatField(null=True)


class PreOrderReadSystem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_id: str
    date: datetime.datetime

    info: order_models.OrderInfoRead
    price: PreOrderPriceSystem


class PreOrderReadUser(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_id: str

    info: order_models.OrderInfoRead
    price: PreOrderPriceUser
