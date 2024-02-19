from pydantic import BaseModel


from src.core import enums

__all__ = (
    "UserNotificationRead",
    "UserNotificationCreate",
    "NotificationSendUser",
    "NotificationSendSystem",
)

from src.models import NotificationType
from src.schemas.auth import UserRead


class UserNotificationRead(BaseModel):
    user_id: int
    type: enums.Integration


class UserNotificationCreate(BaseModel):
    type: enums.Integration


class NotificationSendUser(BaseModel):
    user: UserRead
    type: NotificationType
    data: dict | None = None


class NotificationSendSystem(BaseModel):
    type: NotificationType
    data: dict
