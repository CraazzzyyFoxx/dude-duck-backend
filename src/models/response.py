from datetime import datetime, timedelta

from sqlalchemy import BigInteger, Boolean, DateTime, Float, ForeignKey, Interval, Select, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core import db
from src.models.auth import User

__all__ = ("Response", )


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
