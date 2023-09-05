from datetime import datetime
from enum import Enum

from beanie import PydanticObjectId
from pydantic import BaseModel, Field, model_validator, field_validator


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

    @model_validator(mode='after')
    def spreadsheet_sheet_together(self):
        if self.sheet_id is not None and self.spreadsheet is None:
            raise ValueError("Spreadsheet and sheet_id are related, you must specify them together")


class AccountingReportItem(BaseModel):
    order_id: str
    username: str
    dollars: float
    rub: float
    dollars_fee: float
    date_end: datetime
    payment: str
    bank: str
    status: bool


class AccountingReport(BaseModel):
    total: float
    total_rub: float
    users: int
    orders: int
    earned: float
    items: list[AccountingReportItem]


class UserOrderRead(BaseModel):
    order: PydanticObjectId = Field(serialization_alias="order_id")
    user: PydanticObjectId = Field(serialization_alias="user_id")
    dollars: float
    completed: bool
    paid: bool
    paid_time: datetime | None
    method_payment: str

    @field_validator("order", mode="before")
    def order_id_resolver(cls, v):
        return v.id

    @field_validator("user", mode="before")
    def user_id_resolver(cls, v):
        return v.id


class OrderBoosterCreate(BaseModel):
    user_id: PydanticObjectId
    dollars: float
    method_payment: str
