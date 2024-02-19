import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, HttpUrl
from sqlalchemy import Select

from src.core import pagination
from src.models.order import (
    Order,
    OrderInfo,
    OrderPaidStatus,
    OrderStatus,
    Screenshot,
)

__all__ = (
    "OrderPriceUser",
    "OrderPriceSystem",
    "OrderReadHasPerms",
    "OrderReadNoPerms",
    "OrderReadSystemMeta",
    "OrderReadSystemBase",
    "OrderReadSystem",
    "OrderReadActive",
    "OrderStatusFilter",
    "OrderFilterParams",
    "ScreenshotParams",
    "OrderCreate",
    "OrderUpdate",
    "OrderInfoMetaRead",
    "OrderInfoRead",
    "OrderPriceMeta",
    "OrderPriceNone",
    "OrderPriceRead",
    "OrderCredentialsRead",
    "ScreenshotRead",
    "ScreenshotCreate",
)


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
    booster_dollar_fee: float | None = None
    booster_dollar: float | None = None
    booster_gold: float | None = None


class OrderPriceNone(OrderPriceMeta):
    dollar: float | None = None


class OrderPriceRead(OrderPriceNone):
    dollar: float
    booster_dollar: float
    booster_dollar_fee: float


class OrderCredentialsRead(BaseModel):
    battle_tag: str | None = None
    nickname: str | None = None
    login: str | None = None
    password: str | None = None
    vpn: str | None = None
    discord: str | None = None


class ScreenshotRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime.datetime

    source: str
    url: HttpUrl
    order_id: int
    user_id: int


class ScreenshotCreate(BaseModel):
    order_id: int
    url: HttpUrl


class OrderCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    order_id: str
    spreadsheet: str
    sheet_id: int
    row_id: int

    date: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.UTC))
    shop: str | None = None
    shop_order_id: str | int | None = None

    status: OrderStatus
    status_paid: OrderPaidStatus

    info: OrderInfoRead
    price: OrderPriceRead
    credentials: OrderCredentialsRead

    auth_date: datetime.datetime | None = None
    end_date: datetime.datetime | None = None


class OrderUpdate(BaseModel):
    shop: str | None = Field(default=None)
    shop_order_id: str | None = Field(default=None)

    status: OrderStatus | None = Field(default=None)
    status_paid: OrderPaidStatus | None = Field(default=None)

    info: OrderInfoMetaRead | None = Field(default=None)
    price: OrderPriceNone | None = Field(default=None)
    credentials: OrderCredentialsRead | None = Field(default=None)

    auth_date: datetime.datetime | None = Field(default=None)
    end_date: datetime.datetime | None = Field(default=None)


class OrderPriceUser(OrderPriceMeta):
    booster_dollar_fee: float
    booster_rub: float
    booster_gold: float | None = None


class OrderPriceSystem(OrderPriceNone):
    dollar: float
    booster_dollar_fee: float
    booster_rub: float


class OrderReadHasPerms(BaseModel):
    id: int
    order_id: str
    status: OrderStatus

    screenshots: list[ScreenshotRead]

    info: OrderInfoRead
    price: OrderPriceUser
    credentials: OrderCredentialsRead


class OrderReadNoPerms(BaseModel):
    id: int
    order_id: str

    info: OrderInfoRead
    price: OrderPriceUser


class OrderReadSystemMeta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    order_id: str
    date: datetime.datetime

    shop: str | None
    shop_order_id: str | None

    status: OrderStatus
    status_paid: OrderPaidStatus

    info: OrderInfoRead
    price: OrderPriceNone
    credentials: OrderCredentialsRead

    auth_date: datetime.datetime | None
    end_date: datetime.datetime | None


class OrderReadSystemBase(OrderReadSystemMeta):
    model_config = ConfigDict(from_attributes=True)

    screenshots: list[ScreenshotRead]


class OrderReadSystem(OrderReadSystemBase):
    id: int
    price: OrderPriceSystem


class OrderReadActive(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_id: str
    status: OrderStatus

    info: OrderInfoRead
    price: OrderPriceUser
    credentials: OrderCredentialsRead

    screenshots: list[ScreenshotRead]

    paid_at: datetime.datetime | None
    auth_date: datetime.datetime | None = None
    end_date: datetime.datetime | None = None


class OrderStatusFilter(Enum):
    Refund = "Refund"
    InProgress = "In Progress"
    Completed = "Completed"
    All = "all"


class OrderFilterParams(pagination.PaginationParams):
    status: OrderStatusFilter = OrderStatusFilter.All
    order_id: list[str] | None = None
    ids: list[int] | None = None
    game: str | None = None

    def apply_filters(self, query: Select) -> Select:
        if self.order_id and not self.ids:
            query = query.where(Order.order_id.in_(self.order_id))
        elif self.ids and not self.order_id:
            query = query.where(Order.id.in_(self.ids))
        elif self.ids and self.order_id:
            query = query.where(Order.order_id.in_(self.order_id) | Order.id.in_(self.ids))

        if self.game:
            query = query.where(Order.info.has(OrderInfo.game == self.game))

        if self.status != OrderStatusFilter.All:
            query = query.where(Order.status == OrderStatus(self.status.value))
        return query


class ScreenshotParams(pagination.PaginationParams):
    order_id: int | None = None
    user_id: int | None = None
    source: str | None = None

    def apply_filters(self, query: Select) -> Select:
        if self.order_id:
            query = query.where(Screenshot.order_id == self.order_id)
        if self.user_id:
            query = query.where(Screenshot.user_id == self.user_id)
        if self.source:
            query = query.where(Screenshot.source.like(f"%{self.source}%"))
        return query
