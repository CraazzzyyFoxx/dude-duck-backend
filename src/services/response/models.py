from datetime import datetime, timedelta

from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, ForeignKey, DateTime, Float, Boolean, Interval, BigInteger

from src.core.db import TimeStampMixin
from src.services.auth import models as auth_models


class ResponseExtra(BaseModel):
    text: str | None = None
    price: float | None = None
    start_date: datetime | None = None
    eta: timedelta | None = None


class Response(TimeStampMixin):
    __tablename__ = "response"

    refund: Mapped[bool] = mapped_column(Boolean(), default=False)
    approved: Mapped[bool] = mapped_column(Boolean(), default=False)
    closed: Mapped[bool] = mapped_column(Boolean(), default=False)

    text: Mapped[str | None] = mapped_column(String(), nullable=True)
    price: Mapped[float | None] = mapped_column(Float(), nullable=True)
    start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    eta: Mapped[timedelta | None] = mapped_column(Interval(), nullable=True)

    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    user: Mapped["auth_models.User"] = relationship()
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
