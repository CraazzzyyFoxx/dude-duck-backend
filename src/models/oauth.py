from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core import db
from src.models.auth import User


__all__ = ("OAuthUser", )


class OAuthUser(db.TimeStampMixin):
    __tablename__ = "oauth_users"

    oauth_name: Mapped[str] = mapped_column(String(length=100), index=True, nullable=False)
    access_token: Mapped[str] = mapped_column(String(length=1024), nullable=False)
    expires_at: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    refresh_token: Mapped[str | None] = mapped_column(String(length=1024), nullable=True)
    account_id: Mapped[str] = mapped_column(String(length=320), index=True, nullable=False)
    account_email: Mapped[str | None] = mapped_column(String(length=320), nullable=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    user: Mapped["User"] = relationship()
