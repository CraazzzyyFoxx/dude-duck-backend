import typing

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, constr, model_validator
from tortoise import fields
from tortoise.signals import pre_save

from app.core.db import TimeStampMixin
from app.services.auth import models as auth_models
from app.services.orders import models as order_models


class FirstSort(str, Enum):
    ORDER = "order"
    DATE = "date"


class SecondSort(str, Enum):
    ORDER = "order"
    USER = "user"


class UserOrder(TimeStampMixin):
    order: fields.ForeignKeyRelation[order_models.Order] = fields.ForeignKeyField("main.Order")
    user: fields.ForeignKeyRelation[auth_models.User] = fields.ForeignKeyField("main.User")
    dollars: float = fields.FloatField()
    completed: bool = fields.BooleanField(default=False)
    paid: bool = fields.BooleanField(default=False)
    paid_at: datetime | None = fields.DatetimeField(null=True)
    method_payment: str = fields.CharField(max_length=20, default="$")

    order_date: datetime = fields.DatetimeField()
    completed_at: datetime | None = fields.DatetimeField(null=True)

    user_id: int
    order_id: int

    class Meta:
        unique_together = ("order_id", "user_id")


@pre_save(UserOrder)
async def signal_pre_save(sender: "typing.Type[UserOrder]", instance: UserOrder, using_db, update_fields) -> None:
    instance.updated_at = datetime.utcnow()
    instance.completed_at = datetime.utcnow() if instance.completed is True else None
    instance.paid_at = datetime.utcnow() if instance.paid is True else None


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


class AccountingReportSheetsForm(BaseModel):
    start_date: datetime
    end_date: datetime
    spreadsheet: str | None = Field(default=None)
    sheet_id: int | None = Field(default=None)
    username: str | None = Field(default=None)
    first_sort: FirstSort
    second_sort: SecondSort
    is_completed: bool = Field(default=True)
    is_paid: bool = Field(default=False)

    @model_validator(mode="after")
    def spreadsheet_sheet_together(self) -> "AccountingReportSheetsForm":
        if self.sheet_id is not None and self.spreadsheet is None:
            raise ValueError("Spreadsheet and sheet_id are related, you must specify them together")
        return self


class AccountingReportItem(BaseModel):
    order_id: str
    date: datetime
    username: str
    dollars: float
    rub: float
    dollars_fee: float
    end_date: datetime | None
    payment: str
    bank: str
    status: order_models.OrderStatus
    payment_id: int


class AccountingReport(BaseModel):
    total: float
    orders: int
    earned: float
    items: list[AccountingReportItem]


class UserOrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    order_id: int
    user_id: int
    dollars: float
    completed: bool
    paid: bool
    paid_at: datetime | None
    order_date: datetime
    completed_at: datetime | None
    method_payment: str


class OrderBoosterCreate(BaseModel):
    user_id: int
    dollars: float | None = None
    method_payment: str | None = None
