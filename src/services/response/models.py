from datetime import datetime, timedelta

from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Mapped, mapped_column, relationship, declared_attr
from sqlalchemy import String, ForeignKey, DateTime, Float, Boolean, Interval, UniqueConstraint

from src.core.db import TimeStampMixin
from src.services.auth import models as auth_models
from src.services.orders import models as order_models
from src.services.preorders import models as preorder_models


class ResponseExtra(BaseModel):
    text: str | None = None
    price: float | None = None
    start_date: datetime | None = None
    eta: timedelta | None = None


class BaseResponse(TimeStampMixin):
    __abstract__ = True

    refund: Mapped[bool] = mapped_column(Boolean(), default=False)
    approved: Mapped[bool] = mapped_column(Boolean(), default=False)
    closed: Mapped[bool] = mapped_column(Boolean(), default=False)

    text: Mapped[str | None] = mapped_column(String(), nullable=True)
    price: Mapped[float | None] = mapped_column(Float(), nullable=True)
    start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    eta: Mapped[timedelta | None] = mapped_column(Interval(), nullable=True)

    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    @declared_attr
    def user_id(cls):  # noqa
        return mapped_column(ForeignKey("user.id"))

    @declared_attr
    def user(cls):  # noqa
        return relationship()


class Response(BaseResponse):
    __tablename__ = "response"

    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    user: Mapped["auth_models.User"] = relationship()
    order_id: Mapped[int] = mapped_column(ForeignKey("order.id"))
    order: Mapped["order_models.Order"] = relationship()

    __table_args__ = (
        # Index("idx_user_order", user_id, order_id, unique=True),
        UniqueConstraint(user_id, order_id),
    )


class PreResponse(BaseResponse):
    __tablename__ = "pre_response"

    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    user: Mapped["auth_models.User"] = relationship()
    order_id: Mapped[int] = mapped_column(ForeignKey("preorder.id"))
    order: Mapped["preorder_models.PreOrder"] = relationship()

    __table_args__ = (
        # Index("idx_user_preorder", user_id, order_id, unique=True),
        UniqueConstraint(user_id, order_id),
    )


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
