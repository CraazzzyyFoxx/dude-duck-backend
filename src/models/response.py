from datetime import datetime, timedelta

from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Boolean, DateTime, Float, ForeignKey, Interval, Select, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core import db, pagination
from src.models.auth import User

__all__ = ("ResponseExtra", "ResponseCreate", "ResponseRead", "ResponseUpdate", "Response", "ResponsePagination")


class ResponseExtra(BaseModel):
    text: str | None = None
    price: float | None = None
    start_date: datetime | None = None
    eta: timedelta | None = None


class Response(db.TimeStampMixin):
    __tablename__ = "response"

    refund: Mapped[bool] = mapped_column(Boolean(), default=False)
    approved: Mapped[bool] = mapped_column(Boolean(), default=False)
    closed: Mapped[bool] = mapped_column(Boolean(), default=False)

    text: Mapped[str | None] = mapped_column(String(), nullable=True)
    price: Mapped[float | None] = mapped_column(Float(), nullable=True)
    start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    eta: Mapped[timedelta | None] = mapped_column(Interval(), nullable=True)

    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user_id: Mapped[int] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"))
    user: Mapped["User"] = relationship()
    order_id: Mapped[int] = mapped_column(BigInteger())
    is_preorder: Mapped[bool] = mapped_column(Boolean(), default=False)


class ResponseCreate(BaseModel):
    order_id: int
    user_id: int

    text: str | None = None
    price: float | None = None
    start_date: datetime | None = None
    eta: timedelta | None = None


class ResponseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
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


class ResponsePagination(pagination.PaginationParams):
    order_id: int | None = None
    user_id: int | None = None
    is_preorder: bool | None = None

    def apply_filter(self, query: Select) -> Select:
        if self.order_id is not None:
            query = query.where(Response.order_id == self.order_id)
        if self.user_id is not None:
            query = query.where(Response.user_id == self.user_id)
        if self.is_preorder is not None:
            query = query.where(Response.is_preorder == self.is_preorder)
        return query
