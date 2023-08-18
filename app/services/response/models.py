import datetime

from pydantic import BaseModel, Field, ConfigDict, field_validator
from beanie import Document, PydanticObjectId, Link
from pymongo import IndexModel

from app.services.auth.models import User
from app.services.orders.models import Order

__all__ = (
    "OrderResponseExtra",
    "OrderResponse",
    "OrderResponseUpdate",
    "OrderResponseCreate",
    "OrderResponseRead"
)


class OrderResponseExtra(BaseModel):
    text: str | None = None
    price: float | None = None
    start_date: datetime.datetime | None = None
    eta: datetime.timedelta | None = None


class OrderResponse(Document):
    order: Link[Order]
    user: Link[User]

    refund: bool = Field(default=False)
    approved: bool = Field(default=False)
    closed: bool = Field(default=False)
    extra: OrderResponseExtra

    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    approved_at: datetime.datetime | None = None

    class Settings:
        indexes = [
            IndexModel(["order", "user"], unique=True),
        ]
        use_state_management = True
        state_management_save_previous = True


class OrderResponseCreate(BaseModel):
    extra: OrderResponseExtra


class OrderResponseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    order: PydanticObjectId = Field(serialization_alias="order_id")
    user: PydanticObjectId = Field(serialization_alias="user_id")

    refund: bool
    approved: bool
    closed: bool
    extra: OrderResponseExtra

    @field_validator("order", mode="before")
    def order_id_resolver(cls, v):
        return v.id

    @field_validator("user", mode="before")
    def user_id_resolver(cls, v):
        return v.id


class OrderResponseUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    refund: bool
    approved: bool
    closed: bool
