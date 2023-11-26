import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict
from sqlalchemy import Select

from src.core import pagination

from .models import (
    Order,
    OrderCredentialsRead,
    OrderInfoRead,
    OrderPaidStatus,
    OrderPriceMeta,
    OrderPriceNone,
    OrderStatus,
    Screenshot,
    ScreenshotRead,
)


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
    contact: str | None

    status: OrderStatus
    status_paid: OrderPaidStatus

    info: OrderInfoRead
    price: OrderPriceNone
    credentials: OrderCredentialsRead

    auth_date: datetime.datetime | None = None
    end_date: datetime.datetime | None = None


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

    def apply_filters(self, query: Select) -> Select:
        if self.order_id and not self.ids:
            query = query.where(Order.order_id.in_(self.order_id))
        elif self.ids and not self.order_id:
            query = query.where(Order.id.in_(self.ids))
        elif self.ids and self.order_id:
            query = query.where(Order.order_id.in_(self.order_id) | Order.id.in_(self.ids))

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
