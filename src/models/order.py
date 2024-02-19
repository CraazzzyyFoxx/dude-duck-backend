import enum
from datetime import UTC, datetime

from sqlalchemy import BigInteger, DateTime, Enum, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core import db

from .auth import User

__all__ = (
    "OrderStatus",
    "OrderPaidStatus",
    "Order",
    "OrderInfo",
    "OrderPrice",
    "OrderCredentials",
    "Screenshot",
)


class OrderStatus(enum.Enum):
    Refund = "Refund"
    InProgress = "In Progress"
    Completed = "Completed"


class OrderPaidStatus(enum.Enum):
    Paid = "Paid"
    NotPaid = "Not Paid"


class Order(db.TimeStampMixin):
    __tablename__ = "order"

    order_id: Mapped[str] = mapped_column(String(10))
    spreadsheet: Mapped[str] = mapped_column(String())
    sheet_id: Mapped[int] = mapped_column(BigInteger())
    row_id: Mapped[int] = mapped_column(BigInteger())

    date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    shop: Mapped[str | None] = mapped_column(String(), nullable=True)
    shop_order_id: Mapped[str | None] = mapped_column(String(), nullable=True)

    status: Mapped[OrderStatus] = mapped_column(Enum(OrderStatus))
    status_paid: Mapped[OrderPaidStatus] = mapped_column(Enum(OrderPaidStatus))
    auth_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    info: Mapped["OrderInfo"] = relationship(uselist=False)
    price: Mapped["OrderPrice"] = relationship(uselist=False)
    credentials: Mapped["OrderCredentials"] = relationship(uselist=False)
    screenshots: Mapped[list["Screenshot"]] = relationship(uselist=True)


class OrderInfo(db.TimeStampMixin):
    __tablename__ = "order_info"

    order_id: Mapped[int] = mapped_column(ForeignKey("order.id", ondelete="CASCADE"))
    order: Mapped["Order"] = relationship(back_populates="info")
    boost_type: Mapped[str] = mapped_column(String(length=10))
    region_fraction: Mapped[str | None] = mapped_column(String(), nullable=True)
    server: Mapped[str | None] = mapped_column(String(), nullable=True)
    category: Mapped[str | None] = mapped_column(String(), nullable=True)
    character_class: Mapped[str | None] = mapped_column(String(), nullable=True)
    platform: Mapped[str | None] = mapped_column(String(), nullable=True)
    game: Mapped[str] = mapped_column(String())
    purchase: Mapped[str] = mapped_column(String())
    comment: Mapped[str | None] = mapped_column(String(), nullable=True)
    eta: Mapped[str | None] = mapped_column(String(), nullable=True)


class OrderPrice(db.TimeStampMixin):
    __tablename__ = "order_price"

    order_id: Mapped[int] = mapped_column(ForeignKey("order.id", ondelete="CASCADE"))
    order: Mapped["Order"] = relationship(back_populates="price")
    dollar: Mapped[float] = mapped_column(Float())
    booster_dollar: Mapped[float] = mapped_column(Float())
    booster_dollar_fee: Mapped[float] = mapped_column(Float())
    booster_gold: Mapped[float | None] = mapped_column(Float(), nullable=True)


class OrderCredentials(db.TimeStampMixin):
    __tablename__ = "order_credentials"

    order_id: Mapped[int] = mapped_column(ForeignKey("order.id", ondelete="CASCADE"))
    order: Mapped["Order"] = relationship(back_populates="credentials")
    battle_tag: Mapped[str | None] = mapped_column(String(), nullable=True)
    nickname: Mapped[str | None] = mapped_column(String(), nullable=True)
    login: Mapped[str | None] = mapped_column(String(), nullable=True)
    password: Mapped[str | None] = mapped_column(String(), nullable=True)
    vpn: Mapped[str | None] = mapped_column(String(), nullable=True)
    discord: Mapped[str | None] = mapped_column(String(), nullable=True)


class Screenshot(db.TimeStampMixin):
    __tablename__ = "screenshot"
    __table_args__ = (UniqueConstraint("order_id", "url", name="uix_order_url"),)

    source: Mapped[str] = mapped_column(String(), nullable=False)
    url: Mapped[str] = mapped_column(String(), nullable=False)
    order_id: Mapped[int] = mapped_column(ForeignKey("order.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"))
    order: Mapped["Order"] = relationship(back_populates="screenshots")
    user: Mapped["User"] = relationship()
