import typing
from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, StringConstraints, model_validator

from src.models.order import OrderStatus

__all__ = (
    "FirstSort",
    "SecondSort",
    "UserOrderCreate",
    "UserOrderRead",
    "UserOrderUpdate",
    "UserAccountReport",
    "CloseOrderForm",
    "AccountingReportSheetsForm",
    "AccountingReportItem",
    "AccountingReport",
)


class FirstSort(str, Enum):
    ORDER = "order"
    DATE = "date"


class SecondSort(str, Enum):
    ORDER = "order"
    USER = "user"


class UserOrderCreate(BaseModel):
    user_id: int
    dollars: float | None = None


class UserOrderUpdate(BaseModel):
    dollars: float | None = None
    completed: bool | None = None
    paid: bool | None = None


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
    message: typing.Annotated[str, StringConstraints(max_length=256, min_length=5)]


class AccountingReportSheetsForm(BaseModel):
    start_date: datetime | date
    end_date: datetime | date
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
    dollars_income: float
    dollars: float
    rub: float
    dollars_fee: float
    end_date: datetime | None
    payment: str
    bank: str
    status: OrderStatus
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
