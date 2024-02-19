import enum

from sqlalchemy import BigInteger, Boolean, Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core import db, enums
from src.models import User

__all__ = (
    "CallbackStatus",
    "Message",
    "OrderMessage",
    "ResponseMessage",
    "UserMessage",
)


class CallbackStatus(str, enum.Enum):
    CREATED = "created"
    UPDATED = "updated"
    DELETED = "deleted"

    NOT_FOUND = "not_found"
    SAME_TEXT = "same_text"
    FORBIDDEN = "forbidden"
    EXISTS = "exists"

    INTEGRATION_NOT_FOUND = "integration not found"


class Message(db.TimeStampMixin):
    __abstract__ = True

    channel_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    message_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    integration: Mapped[enums.Integration] = mapped_column(Enum(enums.Integration))
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)


class OrderMessage(Message):
    __tablename__ = "integration_order_message"

    order_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    is_preorder: Mapped[bool] = mapped_column(Boolean, default=False)


class ResponseMessage(Message):
    __tablename__ = "integration_response_message"

    order_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    user: Mapped[User] = relationship()
    is_preorder: Mapped[bool] = mapped_column(Boolean, default=False)


class UserMessage(Message):
    __tablename__ = "integration_user_message"

    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    user: Mapped[User] = relationship()
