import datetime

from beanie import PydanticObjectId
from pydantic import BaseModel, ConfigDict, Field
from pydantic_core import Url

from app.core.db import TimeStampMixin
from app.services.orders import models as order_models
from app.services.sheets import models as sheets_models


class PreOrderPriceUser(BaseModel):
    price_booster_dollar: float | None = None
    price_booster_rub: float | None = None
    price_booster_gold: float | None = None


class PreOrderPriceSystem(BaseModel):
    price_dollar: float
    price_booster_dollar_without_fee: float | None = None

    price_booster_dollar: float | None = None
    price_booster_rub: float | None = None
    price_booster_gold: float | None = None


class PreOrderCreate(sheets_models.SheetEntity):
    date: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    order_id: str

    info: order_models.OrderInfo
    price: PreOrderPriceUser


class PreOrderUpdate(BaseModel):
    info: order_models.OrderInfo | None = None
    price: PreOrderPriceUser | None = None
    has_response: bool | None = None


class PreOrder(sheets_models.SheetEntity, TimeStampMixin):
    order_id: str
    date: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)

    info: order_models.OrderInfo
    price: order_models.OrderPriceNone
    status: order_models.OrderStatus  # TODO: Убрать, нужен для обратной совместимости с обычным заказом

    has_response: bool = Field(default=False)

    class Settings:
        name = "preorder"
        use_state_management = True
        validate_on_save = True
        bson_encoders = {
            Url: lambda x: str(x),
        }

    def __hash__(self):
        return hash(str(self.id))


class PreOrderReadSystem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: PydanticObjectId
    order_id: str
    date: datetime.datetime

    info: order_models.OrderInfo
    price: PreOrderPriceUser


class PreOrderReadUser(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: PydanticObjectId
    order_id: str

    info: order_models.OrderInfo
    price: PreOrderPriceUser
