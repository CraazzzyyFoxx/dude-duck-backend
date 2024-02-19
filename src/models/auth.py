from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core import db

__all__ = (
    "User",
    "RefreshToken",
    "AccessTokenAPI",
)


class User(db.TimeStampMixin):
    __tablename__ = "user"

    email: Mapped[str] = mapped_column(String(100), unique=True)
    hashed_password: Mapped[str] = mapped_column(Text())
    is_active: Mapped[bool] = mapped_column(default=True)
    is_superuser: Mapped[bool] = mapped_column(default=False)
    is_verified: Mapped[bool] = mapped_column(default=False)
    is_verified_email: Mapped[bool] = mapped_column(default=False)
    name: Mapped[str] = mapped_column(String(20), unique=True)
    max_orders: Mapped[int] = mapped_column(default=3)


class RefreshToken(db.TimeStampMixin):
    __tablename__ = "refresh_token"

    token: Mapped[str] = mapped_column(String(), unique=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"))
    user: Mapped["User"] = relationship()


class AccessTokenAPI(db.TimeStampMixin):
    __tablename__ = "access_token_api"

    token: Mapped[str] = mapped_column(String(100), unique=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"))
    user: Mapped["User"] = relationship()
