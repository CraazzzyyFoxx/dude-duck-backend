from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import BigInteger, String, ForeignKey, DateTime, Float, Boolean

from src.core import db
from src.services.orders import models as order_models
from src.services.sheets import models as sheets_models


class PreOrderPriceUser(BaseModel):
    price_booster_dollar: float | None = None
    price_booster_rub: float | None = None
    price_booster_gold: float | None = None


class PreOrderPriceSystem(BaseModel):
    price_dollar: float | None = None
    price_booster_dollar_without_fee: float | None = None

    price_booster_dollar: float | None = None
    price_booster_rub: float | None = None
    price_booster_gold: float | None = None


class PreOrderCreate(sheets_models.SheetEntity):
    date: datetime = Field(default_factory=datetime.utcnow)
    order_id: str

    info: order_models.OrderInfoRead
    price: PreOrderPriceUser


class PreOrderUpdate(BaseModel):
    info: order_models.OrderInfoRead | None = None
    price: PreOrderPriceUser | None = None
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
    __tablename__ = "preorderinfo"

    order_id: Mapped[int] = mapped_column(ForeignKey("preorder.id"))
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
    __tablename__ = "preorderprice"

    order_id: Mapped[int] = mapped_column(ForeignKey("preorder.id"))
    order: Mapped["PreOrder"] = relationship(back_populates="price")
    price_dollar: Mapped[float] = mapped_column(Float())
    price_booster_dollar: Mapped[float] = mapped_column(Float())
    price_booster_gold: Mapped[float | None] = mapped_column(Float(), nullable=True)


class PreOrderReadSystem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_id: str
    date: datetime

    info: order_models.OrderInfoRead
    price: PreOrderPriceSystem


class PreOrderReadUser(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_id: str

    info: order_models.OrderInfoRead
    price: PreOrderPriceUser
