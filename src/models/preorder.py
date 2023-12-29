from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import BigInteger, Boolean, DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src import models
from src.core import db

__all__ = (
    "PreOrderPriceUser",
    "PreOrderPriceSystem",
    "PreOrderCreate",
    "PreOrderUpdate",
    "PreOrder",
    "PreOrderInfo",
    "PreOrderPrice",
    "PreOrderReadSystem",
    "PreOrderReadUser",
)

from src.models.integrations.sheets import SheetEntity


class PreOrderPriceMeta(BaseModel):
    booster_dollar_fee: float | None = None
    booster_dollar: float | None = None
    booster_gold: float | None = None


class PreOrderPriceNone(PreOrderPriceMeta):
    dollar: float | None = None


class PreOrderPriceUser(PreOrderPriceMeta):
    booster_rub: float | None = None


class PreOrderPriceSystem(PreOrderPriceNone):
    booster_rub: float | None = None


class PreOrderCreate(SheetEntity):
    date: datetime = Field(default_factory=lambda: datetime.now(UTC))
    order_id: str

    info: models.OrderInfoRead
    price: models.OrderPriceNone


class PreOrderUpdate(BaseModel):
    info: models.OrderInfoRead | None = None
    price: PreOrderPriceNone | None = None
    has_response: bool | None = None


class PreOrder(db.TimeStampMixin):
    __tablename__ = "preorder"

    order_id: Mapped[str] = mapped_column(String(10))
    spreadsheet: Mapped[str] = mapped_column(String())
    sheet_id: Mapped[int] = mapped_column(BigInteger())
    row_id: Mapped[int] = mapped_column(BigInteger())

    date: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    info: Mapped["PreOrderInfo"] = relationship(uselist=False)
    price: Mapped["PreOrderPrice"] = relationship(uselist=False)

    has_response: Mapped[bool] = mapped_column(Boolean(), default=False)


class PreOrderInfo(db.TimeStampMixin):
    __tablename__ = "preorder_info"

    order_id: Mapped[int] = mapped_column(ForeignKey("preorder.id", ondelete="CASCADE"))
    order: Mapped["PreOrder"] = relationship(back_populates="info")
    boost_type: Mapped[str] = mapped_column(String(length=10))
    region_fraction: Mapped[str | None] = mapped_column(String(), nullable=True)
    server: Mapped[str | None] = mapped_column(String(), nullable=True)
    category: Mapped[str | None] = mapped_column(String(), nullable=True)
    character_class: Mapped[str | None] = mapped_column(String(), nullable=True)
    platform: Mapped[str | None] = mapped_column(String(length=20), nullable=True)
    game: Mapped[str] = mapped_column(String())
    purchase: Mapped[str] = mapped_column(String())
    comment: Mapped[str | None] = mapped_column(String(length=20), nullable=True)
    eta: Mapped[str | None] = mapped_column(String(length=20), nullable=True)


class PreOrderPrice(db.TimeStampMixin):
    __tablename__ = "preorder_price"

    order_id: Mapped[int] = mapped_column(ForeignKey("preorder.id", ondelete="CASCADE"))
    order: Mapped["PreOrder"] = relationship(back_populates="price")
    dollar: Mapped[float] = mapped_column(Float(), nullable=True)
    booster_dollar: Mapped[float] = mapped_column(Float(), nullable=True)
    booster_dollar_fee: Mapped[float] = mapped_column(Float(), nullable=True)
    booster_gold: Mapped[float | None] = mapped_column(Float(), nullable=True)


class PreOrderReadSystem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_id: str
    date: datetime

    info: models.OrderInfoRead
    price: PreOrderPriceSystem


class PreOrderReadUser(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_id: str

    info: models.OrderInfoRead
    price: PreOrderPriceUser
