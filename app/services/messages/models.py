import enum

from pydantic import BaseModel, Field, HttpUrl

from app.services.auth.models import User
from app.services.orders.models import Order
from app.services.response.models import OrderResponseRead


class OrderMessage(BaseModel):
    order_id: str
    channel_id: int
    message_id: int


class OrderPull(BaseModel):
    config_names: list[str] = Field(min_items=1)


class OrderPullCreate(OrderPull):
    categories: list[str]


class OrderPullUpdate(OrderPull):
    pass


class MessageEnum(enum.Enum):
    SEND_ORDER = 0
    EDIT_ORDER = 1
    DELETE_ORDER = 2

    MESSAGE_RESPONSE = 3
    RESPONSE_APPROVED = 4
    RESPONSE_DECLINED = 5
    REQUEST_VERIFY = 6
    VERIFIED = 7

    REQUEST_CLOSE_ORDER = 8


class MessageEventPayload(BaseModel):
    order: Order | None = Field(default=None)
    categories: list[str] | None = Field(default=None)
    configs: list[str] | None = Field(default=None)
    user: User | None = Field(default=None)
    response: OrderResponseRead | None = Field(default=None)
    token: str | None = Field(default=None)
    url: HttpUrl | None = Field(default=None)
    message: str | None = Field(default=None)


class MessageEvent(BaseModel):
    type: MessageEnum
    payload: MessageEventPayload
