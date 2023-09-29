from datetime import datetime

from beanie import Link, PydanticObjectId
from pydantic import BaseModel, Field, HttpUrl, constr, field_validator, model_validator
from pymongo import IndexModel

from app.core.db import TimeStampMixin
from app.services.auth import models as auth_models
from app.services.orders import models as order_models


class UserOrder(TimeStampMixin):
    order_id: Link[order_models.Order]
    user_id: Link[auth_models.User]
    dollars: float
    completed: bool = Field(default=False)
    paid: bool = Field(default=False)
    method_payment: str = Field(default="$")

    order_date: datetime
    created_at: datetime = Field(default_factory=datetime.utcnow)
    paid_at: datetime | None = Field(default=None)
    completed_at: datetime | None = Field(default=None)

    class Settings:
        name = "order_user"
        indexes = [
            IndexModel(["order_id", "user_id"], unique=True),
        ]
        use_state_management = True
        state_management_save_previous = True
        validate_on_save = True


class UserOrderCreate(BaseModel):
    order_id: PydanticObjectId
    user_id: PydanticObjectId
    dollars: float
    completed: bool = Field(default=False)
    paid: bool = Field(default=False)
    method_payment: str = Field(default="$")
    order_date: datetime


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


class CloseOrderForm(BaseModel):
    url: HttpUrl
    message: constr(max_length=256, min_length=5)
