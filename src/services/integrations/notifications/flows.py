from sqlalchemy.ext.asyncio import AsyncSession

from src import models, schemas
from src.core import enums
from src.services.integrations.telegram import service as telegram_service

from . import service


async def get_user_accounts(session: AsyncSession, user: schemas.UserRead) -> schemas.UserReadWithAccounts:
    telegram_account = await telegram_service.get_tg_account(session, user.id)
    return schemas.UserReadWithAccounts(
        telegram=schemas.TelegramAccountRead.model_validate(telegram_account, from_attributes=True)
        if telegram_account
        else None,
        **user.model_dump(),
    )


def send_response_approved(
    user: schemas.UserRead,
    order: schemas.OrderReadSystem,
    response: schemas.ResponseRead,
    text: str,
) -> None:
    service.send_user_notification(
        schemas.NotificationSendUser(
            type=models.NotificationType.ORDER_RESPONSE_APPROVE,
            user=user,
            data={"order": order, "response": response, "text": text},
        )
    )


def send_response_declined(user: schemas.UserRead, order_id: str) -> None:
    service.send_user_notification(
        schemas.NotificationSendUser(
            type=models.NotificationType.ORDER_RESPONSE_DECLINE,
            user=user,
            data={"order_id": order_id},
        )
    )


def send_logged_notify(user: schemas.UserReadWithAccounts, integration: enums.Integration) -> None:
    service.send_system_notification(
        schemas.NotificationSendSystem(
            type=models.NotificationType.LOGGED_NOTIFY, data={"user": user, "integration": integration}
        ),
    )


def send_registered_notify(user: schemas.UserReadWithAccounts, integration: enums.Integration) -> None:
    service.send_system_notification(
        schemas.NotificationSendSystem(
            type=models.NotificationType.REGISTERED_NOTIFY, data={"user": user, "integration": integration}
        ),
    )


def send_verified_notify(user: schemas.UserReadWithAccounts) -> None:
    service.send_user_notification(schemas.NotificationSendUser(type=models.NotificationType.VERIFIED_NOTIFY, user=user))


def send_request_verify(user: schemas.UserReadWithAccounts) -> None:
    service.send_system_notification(
        schemas.NotificationSendSystem(type=models.NotificationType.REQUEST_VERIFY, data={"user": user})
    )


def send_order_close_notify(user: schemas.UserRead, order_id: str, url: str, message: str) -> None:
    service.send_system_notification(
        schemas.NotificationSendSystem(
            type=models.NotificationType.ORDER_CLOSE_REQUEST,
            data={"user": user, "order_id": order_id, "url": url, "message": message},
        )
    )


def send_sent_order_notify(order_id: str, integration: enums.Integration, payload: schemas.MessageCallback) -> None:
    service.send_system_notification(
        schemas.NotificationSendSystem(
            type=models.NotificationType.ORDER_SENT_NOTIFY,
            data={"order_id": order_id, "integration": integration, "payload": payload},
        )
    )


def send_edited_order_notify(order_id: str, integration: enums.Integration, payload: schemas.MessageCallback) -> None:
    service.send_system_notification(
        schemas.NotificationSendSystem(
            type=models.NotificationType.ORDER_EDITED_NOTIFY,
            data={"order_id": order_id, "integration": integration,  "payload": payload},
        )
    )


def send_deleted_order_notify(order_id: str, integration: enums.Integration, payload: schemas.MessageCallback) -> None:
    service.send_system_notification(
        schemas.NotificationSendSystem(
            type=models.NotificationType.ORDER_DELETED_NOTIFY,
            data={"order_id": order_id, "integration": integration,  "payload": payload},
        )
    )


def send_response_chose_notify(order_id: str, user: schemas.UserReadWithAccounts, responses: int) -> None:
    service.send_system_notification(
        schemas.NotificationSendSystem(
            type=models.NotificationType.RESPONSE_CHOSE_NOTIFY,
            data={"order_id": order_id, "user": user, "responses": responses},
        )
    )


def send_order_paid_notify(order: schemas.OrderReadSystem, user: schemas.UserRead) -> None:
    service.send_system_notification(
        schemas.NotificationSendSystem(
            type=models.NotificationType.ORDER_PAID_NOTIFY,
            data={"order": order, "user": user},
        )
    )
