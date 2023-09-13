import datetime

from beanie import PydanticObjectId
from pydantic import BaseModel

__all__ = (
    "OrderRead",
    "OrderPriceUser",
    "OrderReadBase",
    "OrderReadUser",
)

from .models import (OrderCredentials, OrderInfo, OrderPaidStatus, OrderPrice,
                     OrderStatus)


class OrderPriceUser(BaseModel):
    price_booster_dollar_fee: float
    price_booster_rub: float
    price_booster_gold: float | None = None


class OrderReadMeta(BaseModel):
    order_id: str

    date: datetime.datetime
    screenshot: str | None

    status: OrderStatus
    info: OrderInfo

    auth_date: datetime.datetime | None
    end_date: datetime.datetime | None


class OrderReadBase(OrderReadMeta):
    shop: str | None
    shop_order_id: str | int | None
    contact: str | None
    booster: str | None

    status_paid: OrderPaidStatus

    price: OrderPrice
    credentials: OrderCredentials


class OrderRead(OrderReadBase):
    id: PydanticObjectId


class OrderReadUser(OrderReadMeta):
    id: PydanticObjectId

    price: OrderPriceUser
    credentials: OrderCredentials | None = None
