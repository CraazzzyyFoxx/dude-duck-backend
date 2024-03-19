from sqlalchemy import BigInteger, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core import db
from src.models.auth import User

__all__ = ("TelegramAccount", )


class TelegramAccount(db.TimeStampMixin):
    __tablename__ = "telegram_account"

    account_id: Mapped[int] = mapped_column(BigInteger(), nullable=False)
    username: Mapped[str] = mapped_column(String(255), nullable=False)
    first_name: Mapped[str] = mapped_column(String(255), nullable=False)

    user_id: Mapped[int] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"), nullable=False, unique=True)
    user: Mapped["User"] = relationship()
