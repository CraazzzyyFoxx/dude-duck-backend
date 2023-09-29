from datetime import datetime
from enum import Enum

from beanie import Link, PydanticObjectId
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.services.orders import models as order_models


class FirstSort(str, Enum):
    ORDER = "order"
    DATE = "date"


class SecondSort(str, Enum):
    ORDER = "order"
    USER = "user"


class AccountingReportSheetsForm(BaseModel):
    start_date: datetime
    end_date: datetime
    spreadsheet: str | None = Field(default=None)
    sheet_id: int | None = Field(default=None)
    username: str | None = Field(default=None)
    first_sort: FirstSort
    second_sort: SecondSort

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
    payment_id: PydanticObjectId


class AccountingReport(BaseModel):
    total: float
    orders: int
    earned: float
    items: list[AccountingReportItem]


class UserOrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    order_id: PydanticObjectId
    user_id: PydanticObjectId
    dollars: float
    completed: bool
    paid: bool
    paid_time: datetime | None
    order_date: datetime
    completed_at: datetime | None
    method_payment: str

    @field_validator("order_id", "user_id", mode="before")
    def link_converter(self, v: Link) -> PydanticObjectId:
        return v.ref.id


class OrderBoosterCreate(BaseModel):
    user_id: PydanticObjectId
    dollars: float | None = None
    method_payment: str | None = None
