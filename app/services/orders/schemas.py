import datetime

from beanie import PydanticObjectId
from pydantic import BaseModel, ConfigDict

from .models import OrderCredentials, OrderInfo, OrderPaidStatus, OrderStatus, OrderPrice


class OrderPriceUser(OrderPrice):
    price_booster_dollar: float
    price_booster_rub: float
    price_booster_gold: float | None = None


class OrderPriceSystem(OrderPrice):
    price_dollar: float
    price_booster_dollar_without_fee: float

    price_booster_dollar: float
    price_booster_rub: float
    price_booster_gold: float | None = None


class OrderReadHasPerms(BaseModel):
    id: PydanticObjectId
    order_id: str
    screenshot: str | None
    status: OrderStatus

    info: OrderInfo
    price: OrderPriceUser
    credentials: OrderCredentials


class OrderReadNoPerms(BaseModel):
    id: PydanticObjectId
    order_id: str

    info: OrderInfo
    price: OrderPriceUser


class OrderReadSystemBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    order_id: str
    date: datetime.datetime

    shop: str | None
    shop_order_id: str | int | None
    contact: str | None

    screenshot: str | None

    status: OrderStatus
    status_paid: OrderPaidStatus

    info: OrderInfo
    price: OrderPriceSystem
    credentials: OrderCredentials

    auth_date: datetime.datetime | None = None
    end_date: datetime.datetime | None = None


class OrderReadSystem(OrderReadSystemBase):
    id: PydanticObjectId


class OrderReadActive(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: PydanticObjectId
    order_id: str
    screenshot: str | None
    status: OrderStatus

    info: OrderInfo
    price: OrderPriceUser
    credentials: OrderCredentials

    paid_time: datetime.datetime | None
    auth_date: datetime.datetime | None = None
    end_date: datetime.datetime | None = None
