import datetime
from enum import Enum

from beanie import Document
from pydantic import BaseModel, ConfigDict, Field
from pydantic_core import Url
from pymongo import IndexModel

__all__ = (
    "Order",
    "OrderPrice",
    "OrderInfo",
    "OrderCredentials",
    "OrderUpdate",
    "OrderCreate",
    "OrderStatus",
    "OrderPaidStatus"
)


class OrderStatus(Enum):
    Refund = "Refund"
    InProgress = "In Progress"
    Completed = "Completed"


class OrderPaidStatus(Enum):
    Paid = "Paid"
    NotPaid = "Not Paid"


class SheetEntity(BaseModel):
    spreadsheet: str
    sheet_id: int
    row_id: int


class OrderInfo(BaseModel):
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


class OrderPrice(BaseModel):
    price_dollar: float | None = None
    price_booster_dollar: float | None = None


class OrderCredentials(BaseModel):
    battle_tag: str | None = None
    nickname: str | None = None
    login: str | None = None
    password: str | None = None
    vpn: str | None = None
    discord: str | None = None


class OrderCreate(SheetEntity, BaseModel):
    order_id: str

    date: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    shop: str | None = None
    shop_order_id: str | int | None = None
    contact: str | None = None
    screenshot: str | None = None
    booster: str | None = None

    status: OrderStatus
    status_paid: OrderPaidStatus

    info: OrderInfo
    price: OrderPrice
    credentials: OrderCredentials

    auth_date: datetime.datetime | None = None
    end_date: datetime.datetime | None = None


class OrderUpdate(BaseModel):
    shop: str | None = None
    contact: str | None = None
    screenshot: str | None = None
    booster: str | None = None

    status: OrderStatus | None = None
    status_paid: OrderPaidStatus | None = None

    info: OrderInfo | None = None
    price: OrderPrice | None = None
    credentials: OrderCredentials | None = None

    auth_date: datetime.datetime | None = None
    end_date: datetime.datetime | None = None

    archive: bool = False


class Order(SheetEntity, Document):
    model_config = ConfigDict(from_attributes=True)
    order_id: str

    date: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    shop: str | None = None
    shop_order_id: str | int | None = None
    contact: str | None = None
    screenshot: str | None = None
    booster: str | None = None

    status: OrderStatus
    status_paid: OrderPaidStatus

    info: OrderInfo
    price: OrderPrice
    credentials: OrderCredentials

    auth_date: datetime.datetime | None = None
    end_date: datetime.datetime | None = None

    class Settings:
        use_state_management = True
        state_management_save_previous = True
        bson_encoders = {
            Url: lambda x: str(x),
        }
        indexes = [IndexModel("order_id", unique=True)]

    def __hash__(self):
        return hash(str(self.id))
