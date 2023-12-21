import enum

from pydantic import BaseModel
from sqlalchemy import Boolean, Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core import db, enums
from src.models import User, UserRead


class NotificationType(enum.Enum):
    ORDER_RESPONSE_APPROVE = "order_response_approve"
    ORDER_RESPONSE_DECLINE = "order_response_decline"
    ORDER_RESPONSE_ADMIN = "order_response_admin"
    LOGGED_NOTIFY = "logged_notify"
    REGISTERED_NOTIFY = "registered_notify"
    REQUEST_VERIFY = "request_verify"
    VERIFIED_NOTIFY = "verified_notify"
    ORDER_CLOSE_REQUEST = "order_close_request"
    ORDER_SENT_NOTIFY = "order_sent_notify"
    ORDER_EDITED_NOTIFY = "order_edited_notify"
    ORDER_DELETED_NOTIFY = "order_deleted_notify"
    RESPONSE_CHOSE_NOTIFY = "response_chose_notify"
    ORDER_PAID_NOTIFY = "order_paid_notify"


class UserNotification(db.TimeStampMixin):
    __tablename__ = "user_notifications"

    user_id: Mapped[int] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"))
    user: Mapped[User] = relationship()
    type: Mapped[enums.Integration] = mapped_column(Enum(enums.Integration))
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)


class UserNotificationRead(BaseModel):
    user_id: int
    type: enums.Integration
    enabled: bool


class UserNotificationCreate(BaseModel):
    type: enums.Integration
    enabled: bool


class UserNotificationUpdate(BaseModel):
    enabled: bool


class NotificationSendUser(BaseModel):
    user: UserRead
    type: NotificationType
    data: dict | None = None


class NotificationSendSystem(BaseModel):
    type: NotificationType
    data: dict
