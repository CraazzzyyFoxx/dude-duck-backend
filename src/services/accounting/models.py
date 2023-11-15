from datetime import datetime, UTC
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, constr, model_validator
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, ForeignKey, Float, Boolean, DateTime, UniqueConstraint, event

from src.core import db, pagination
from src.services.auth import models as auth_models
from src.services.order import models as order_models


class FirstSort(str, Enum):
    ORDER = "order"
    DATE = "date"


class SecondSort(str, Enum):
    ORDER = "order"
    USER = "user"


class UserOrder(db.TimeStampMixin):
    __tablename__ = "user_order"

    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    user: Mapped["auth_models.User"] = relationship()
    order_id: Mapped[int] = mapped_column(ForeignKey("order.id"))
    order: Mapped["order_models.Order"] = relationship()
    dollars: Mapped[float] = mapped_column(Float())
    completed: Mapped[bool] = mapped_column(Boolean(), default=False)
    paid: Mapped[bool] = mapped_column(Boolean(), default=False)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    method_payment: Mapped[str] = mapped_column(String(20), default="$")

    order_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        # Index("idx_user_order", user_id, order_id, unique=True),
        UniqueConstraint(user_id, order_id, name="u_user_order"),
    )


@event.listens_for(UserOrder, "before_update")
def receive_before_update(mapper, connection, target):
    target.completed_at = datetime.now(UTC) if target.completed is True else None
    target.paid_at = datetime.now(UTC) if target.paid is True else None


class UserOrderCreate(BaseModel):
    user_id: int
    dollars: float | None = None
    method_payment: str = Field(default="$")


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
    dollars_income: float
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


class UserOrderFilterParams(pagination.PaginationParams):
    status: order_models.OrderStatus
    user_id: int | None = None
