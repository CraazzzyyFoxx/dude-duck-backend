from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, UniqueConstraint, event
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core import db

from .auth import User
from .order import Order

__all__ = (
    "UserOrder",
)


class UserOrder(db.TimeStampMixin):
    __tablename__ = "user_order"
    __table_args__ = (
        # Index("idx_user_order", user_id, order_id, unique=True),
        UniqueConstraint("user_id", "order_id", name="u_user_order"),
    )

    user_id: Mapped[int] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"))
    user: Mapped["User"] = relationship()
    order_id: Mapped[int] = mapped_column(ForeignKey("order.id", ondelete="CASCADE"))
    order: Mapped["Order"] = relationship()
    dollars: Mapped[float] = mapped_column(Float())
    completed: Mapped[bool] = mapped_column(Boolean(), default=False)
    refunded: Mapped[bool] = mapped_column(Boolean(), default=False)
    paid: Mapped[bool] = mapped_column(Boolean(), default=False)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    order_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


@event.listens_for(UserOrder, "before_update")
def receive_before_update(mapper, connection, target):
    target.completed_at = datetime.now(UTC) if target.completed is True else None
    target.paid_at = datetime.now(UTC) if target.paid is True else None
