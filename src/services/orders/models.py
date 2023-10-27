import enum

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import BigInteger, String, ForeignKey, DateTime, Enum, Float

from src.core import db


class OrderStatus(enum.Enum):
    Refund = "Refund"
    InProgress = "In Progress"
    Completed = "Completed"


class OrderPaidStatus(enum.Enum):
    Paid = "Paid"
    NotPaid = "Not Paid"


class OrderInfoMetaRead(BaseModel):
    boost_type: str | None = None
    region_fraction: str | None = None
    server: str | None = None
    category: str | None = None
    character_class: str | None = None
    platform: str | None = None
    game: str | None = None
    purchase: str | None = None
    comment: str | None = None
    eta: str | None = None


class OrderInfoRead(OrderInfoMetaRead):
    boost_type: str
    game: str
    purchase: str


class OrderPriceMeta(BaseModel):
    price_booster_dollar: float | None = None
    price_booster_gold: float | None = None


class OrderPriceNone(OrderPriceMeta):
    price_dollar: float | None = None


class OrderPriceRead(OrderPriceNone):
    price_dollar: float
    price_booster_dollar: float


class OrderCredentialsRead(BaseModel):
    battle_tag: str | None = None
    nickname: str | None = None
    login: str | None = None
    password: str | None = None
    vpn: str | None = None
    discord: str | None = None


class OrderCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    order_id: str
    spreadsheet: str
    sheet_id: int
    row_id: int

    date: datetime = Field(default_factory=datetime.utcnow)
    shop: str | None = None
    shop_order_id: str | int | None = None
    contact: str | None = None

    screenshot: str | None = None

    status: OrderStatus
    status_paid: OrderPaidStatus

    info: OrderInfoRead
    price: OrderPriceRead
    credentials: OrderCredentialsRead

    auth_date: datetime | None = None
    end_date: datetime | None = None


class OrderUpdate(BaseModel):
    shop: str | None = None
    shop_order_id: str | None = None
    contact: str | None = None

    screenshot: str | None = None

    status: OrderStatus | None = None
    status_paid: OrderPaidStatus | None = None

    info: OrderInfoMetaRead | None = None
    price: OrderPriceNone | None = None
    credentials: OrderCredentialsRead | None = None

    auth_date: datetime | None = None
    end_date: datetime | None = None


class Order(db.TimeStampMixin):
    __tablename__ = "order"

    order_id: Mapped[str] = mapped_column(String(10))
    spreadsheet: Mapped[str] = mapped_column(String())
    sheet_id: Mapped[int] = mapped_column(BigInteger())
    row_id: Mapped[int] = mapped_column(BigInteger())

    date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    shop: Mapped[str | None] = mapped_column(String(), nullable=True)
    shop_order_id: Mapped[str | None] = mapped_column(String(), nullable=True)
    contact: Mapped[str | None] = mapped_column(String(), nullable=True)

    screenshot: Mapped[str | None] = mapped_column(String(), nullable=True)

    status: Mapped[OrderStatus] = mapped_column(Enum(OrderStatus))
    status_paid: Mapped[OrderPaidStatus] = mapped_column(Enum(OrderPaidStatus))
    auth_date: Mapped[datetime | None] = mapped_column(DateTime(), nullable=True)
    end_date: Mapped[datetime | None] = mapped_column(DateTime(), nullable=True)

    info: Mapped["OrderInfo"] = relationship(uselist=False)
    price: Mapped["OrderPrice"] = relationship(uselist=False)
    credentials: Mapped["OrderCredentials"] = relationship(uselist=False)


class OrderInfo(db.TimeStampMixin):
    __tablename__ = "orderinfo"

    order_id: Mapped[int] = mapped_column(ForeignKey("order.id"))
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
    __tablename__ = "orderprice"

    order_id: Mapped[int] = mapped_column(ForeignKey("order.id"))
    order: Mapped["Order"] = relationship(back_populates="price")
    price_dollar: Mapped[float] = mapped_column(Float())
    price_booster_dollar: Mapped[float] = mapped_column(Float())
    price_booster_gold: Mapped[float | None] = mapped_column(Float(), nullable=True)


class OrderCredentials(db.TimeStampMixin):
    __tablename__ = "ordercredentials"

    order_id: Mapped[int] = mapped_column(ForeignKey("order.id"))
    order: Mapped["Order"] = relationship(back_populates="credentials")
    battle_tag: Mapped[str | None] = mapped_column(String(), nullable=True)
    nickname: Mapped[str | None] = mapped_column(String(), nullable=True)
    login: Mapped[str | None] = mapped_column(String(), nullable=True)
    password: Mapped[str | None] = mapped_column(String(), nullable=True)
    vpn: Mapped[str | None] = mapped_column(String(), nullable=True)
    discord: Mapped[str | None] = mapped_column(String(), nullable=True)
