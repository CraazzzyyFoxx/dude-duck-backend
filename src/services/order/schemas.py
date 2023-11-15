import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict

from src.core import pagination
from .models import OrderCredentialsRead, OrderInfoRead, OrderPaidStatus, OrderPriceMeta, OrderPriceNone, OrderStatus


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
    screenshot: str | None
    status: OrderStatus

    info: OrderInfoRead
    price: OrderPriceUser
    credentials: OrderCredentialsRead


class OrderReadNoPerms(BaseModel):
    id: int
    order_id: str

    info: OrderInfoRead
    price: OrderPriceUser


class OrderReadSystemBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    order_id: str
    date: datetime.datetime

    shop: str | None
    shop_order_id: str | None
    contact: str | None

    screenshot: str | None

    status: OrderStatus
    status_paid: OrderPaidStatus

    info: OrderInfoRead
    price: OrderPriceSystem
    credentials: OrderCredentialsRead

    auth_date: datetime.datetime | None = None
    end_date: datetime.datetime | None = None


class OrderReadSystem(OrderReadSystemBase):
    id: int


class OrderReadActive(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_id: str
    screenshot: str | None
    status: OrderStatus

    info: OrderInfoRead
    price: OrderPriceUser
    credentials: OrderCredentialsRead

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
