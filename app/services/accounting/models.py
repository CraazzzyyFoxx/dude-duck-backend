import datetime
import enum

from pydantic import BaseModel, Field, model_validator, HttpUrl, constr, field_validator, ConfigDict
from beanie import Document, Link, PydanticObjectId
from pymongo import IndexModel

from app.services.auth.models import User, UserRead
from app.services.orders.models import Order
from app.services.orders.schemas import OrderRead

__all__ = (
    "UserOrder",
    "UserOrderCreate",
    "UserOrderUpdate",
    "UserAccountReport",
    "SheetUserOrderCreate",
    "AccountingBooster"
)


class OrderStatus(str, enum.Enum):
    Completed = "Completed"
    InProgress = "In Progress"
    Refund = "Refund"


class UserOrder(Document, BaseModel):
    order: Link[Order]
    user: Link[User]
    dollars: float
    completed: bool = Field(default=False)
    paid: bool = Field(default=False)
    paid_time: datetime.datetime | None = Field(default=None)
    method_payment: str | None = Field(default="$")

    class Settings:
        indexes = [
            IndexModel(["order", "user"], unique=True),
        ]
        use_state_management = True
        state_management_save_previous = True


class UserOrderCreate(BaseModel):
    order_id: PydanticObjectId
    user_id: PydanticObjectId
    dollars: float
    completed: bool = Field(default=False)
    paid: bool = Field(default=False)
    method_payment: str | None = Field(default="$")


class UserOrderUpdate(BaseModel):
    dollars: float | None = None
    completed: bool | None = None
    paid: bool | None = None
    method_payment: str | None = None


class UserAccountReport(BaseModel):
    total: float
    total_rub: float
    paid: float
    paid_rub: float
    not_paid: float
    not_paid_rub: float

    not_paid_orders: int
    paid_orders: int


class AccountingBooster(BaseModel):
    booster_name: str
    percent: str


class ManageBoosterForm(BaseModel):
    order_id: str
    boosters: list[AccountingBooster]


class UserOrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    order: PydanticObjectId = Field(serialization_alias="order_id")
    user: PydanticObjectId = Field(serialization_alias="user_id")
    dollars: float
    completed: bool
    paid: bool
    paid_time: datetime.datetime | None
    method_payment: str

    @field_validator("order", mode="before")
    def order_id_resolver(cls, v):
        return v.id

    @field_validator("user", mode="before")
    def user_id_resolver(cls, v):
        return v.id


class SheetBoosterOrderEntityCreate(BaseModel):
    username: str
    percent: float = Field(gt=0, lte=1)

    @field_validator("percent", mode="before")
    def percent_resolver(cls, v):
        if v > 1:
            return v / 100
        return v


class SheetUserOrderCreate(BaseModel):
    items: list[SheetBoosterOrderEntityCreate]

    @model_validator(mode='after')
    def check_card_number_omitted(self) -> "SheetUserOrderCreate":  # noqa
        total = 0

        for item in self.items:
            total += item.percent

        if total <= 0.99 or total > 1:
            raise ValueError("The final percentage must be greater or equal 0.99")

        return self  # noqa


class CloseOrderForm(BaseModel):
    url: HttpUrl
    message: constr(max_length=256, min_length=5)
