from datetime import datetime, timedelta

from pydantic import BaseModel, ConfigDict
from tortoise import fields

from app.core.db import TimeStampMixin
from app.services.auth import models as auth_models
from app.services.orders import models as order_models
from app.services.preorders import models as preorder_models


class ResponseExtra(BaseModel):
    text: str | None = None
    price: float | None = None
    start_date: datetime | None = None
    eta: timedelta | None = None


class BaseResponse(TimeStampMixin):
    id: int = fields.BigIntField(pk=True)
    user: fields.ForeignKeyRelation[auth_models.User] = fields.ForeignKeyField("main.User")

    refund: bool = fields.BooleanField(default=False)
    approved: bool = fields.BooleanField(default=False)
    closed: bool = fields.BooleanField(default=False)

    text: str | None = fields.TextField(null=True)
    price: float | None = fields.FloatField(null=True)
    start_date: datetime | None = fields.DatetimeField(null=True)
    eta: timedelta | None = fields.TimeDeltaField(null=True)

    approved_at: datetime | None = fields.DatetimeField(null=True)

    user_id: int
    order_id: int

    class Meta:
        abstract = True


class Response(BaseResponse):
    order: fields.ForeignKeyRelation[order_models.Order] = fields.ForeignKeyField("main.Order")

    class Meta:
        unique_together = ("order_id", "user_id")


class PreResponse(BaseResponse):
    order: fields.ForeignKeyRelation[preorder_models.PreOrder] = fields.ForeignKeyField("main.PreOrder")

    class Meta:
        unique_together = ("order_id", "user_id")


class ResponseCreate(BaseModel):
    order_id: int
    user_id: int

    text: str | None = None
    price: float | None = None
    start_date: datetime | None = None
    eta: timedelta | None = None


class ResponseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    order_id: int
    user_id: int

    refund: bool
    approved: bool
    closed: bool

    text: str | None
    price: float | None
    start_date: datetime | None
    eta: timedelta | None


class ResponseUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    refund: bool | None = None
    approved: bool
    closed: bool
