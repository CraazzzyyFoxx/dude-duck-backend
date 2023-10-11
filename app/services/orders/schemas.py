import datetime

from pydantic import BaseModel, ConfigDict

from .models import OrderCredentialsRead, OrderInfoRead, OrderPaidStatus, OrderPriceMeta, OrderPriceNone, OrderStatus


class OrderPriceUser(OrderPriceMeta):
    price_booster_dollar: float
    price_booster_rub: float
    price_booster_gold: float | None = None


class OrderPriceSystem(OrderPriceNone):
    price_dollar: float
    price_booster_dollar_without_fee: float

    price_booster_rub: float


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
