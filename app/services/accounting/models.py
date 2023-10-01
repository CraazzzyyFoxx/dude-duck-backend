from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl, constr
from tortoise import fields

from app.core.db import TimeStampMixin
from app.services.auth import models as auth_models
from app.services.orders import models as order_models


class UserOrder(TimeStampMixin):
    order: int = fields.BigIntField()
    user: int = fields.BigIntField()
    dollars: float = fields.FloatField()
    completed: bool = fields.BooleanField(default=False)
    paid: bool = fields.BooleanField(default=False)
    paid_at: datetime | None = fields.DatetimeField(null=True)
    method_payment: str = fields.CharField(max_length=20, default="$")

    order_date: datetime = fields.DatetimeField()
    completed_at: datetime | None = fields.DatetimeField(null=True)

    class Meta:
        unique_together = ("order_id", "user_id")


class UserOrderCreate(BaseModel):
    order_id: int
    user_id: int
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
