from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core import db

__all__ = (
    "PreOrder",
    "PreOrderInfo",
    "PreOrderPrice",
)


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
