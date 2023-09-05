import datetime

from beanie import Document, PydanticObjectId
from pydantic import Field, BaseModel
from pydantic_core import Url

from app.services.orders import models as order_models
from app.services.sheets import models as sheets_models

__all__ = (
    "PreOrder",
    "PreOrderUpdate",
    "PreOrderCreate",
)


class PreOrderCreate(BaseModel):
    date: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    order_id: str

    info: order_models.OrderInfo
    price: order_models.OrderPrice


class PreOrderUpdate(BaseModel):
    info: order_models.OrderInfo | None = None
    price: order_models.OrderPrice | None = None


class PreOrder(sheets_models.SheetEntity, Document):
    order_id: str
    date: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)

    info: order_models.OrderInfo
    price: order_models.OrderPrice

    archive: bool = Field(default=False)

    class Settings:
        use_state_management = True
        state_management_save_previous = True
        bson_encoders = {
            Url: lambda x: str(x),
        }

    def __hash__(self):
        return hash(str(self.id))


class PreOrderRead(BaseModel):
    id: PydanticObjectId
    order_id: str
    date: datetime.datetime

    info: order_models.OrderInfo
    price: order_models.OrderPrice
