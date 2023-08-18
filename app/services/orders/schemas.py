import datetime

from beanie import PydanticObjectId
from pydantic import BaseModel

__all__ = (
    "OrderRead",
    "OrderPriceUser",
    "OrderReadBase",
    "OrderReadUser",
)

from .models import OrderInfo, OrderPrice, OrderCredentials


class OrderPriceUser(BaseModel):
    price_booster_dollar_fee: float
    price_booster_rub: float
    price_booster_gold: float | None = None


class OrderReadMeta(BaseModel):
    order_id: str

    date: datetime.datetime
    screenshot: str | None = None
    status: str | None = None  # TODO: оно здесь не надо

    info: OrderInfo

    auth_date: datetime.datetime | None = None
    end_date: datetime.datetime | None = None


class OrderReadBase(OrderReadMeta):
    id: PydanticObjectId

    exchange: float
    shop: str | None = None
    shop_order_id: str | int | None = None
    contact: str | None = None
    booster: str | None = None  # TODO: оно здесь не надо
    status_paid: str | None = None  # TODO: оно здесь не надо

    credentials: OrderCredentials
    price: OrderPrice


class OrderRead(OrderReadBase):
    id: PydanticObjectId


class OrderReadUser(OrderReadMeta):
    price: OrderPriceUser
    credentials: OrderCredentials | None = None