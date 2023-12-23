from sqlalchemy.ext.asyncio import AsyncSession

from src import models, schemas
from src.services.integrations.telegram import service as telegram_service

from . import service


async def get_user_accounts(session: AsyncSession, user: models.UserRead) -> models.UserReadWithAccounts:
    telegram_account = await telegram_service.get_tg_account(session, user.id)
    return models.UserReadWithAccounts(
        telegram=models.TelegramAccountRead.model_validate(telegram_account, from_attributes=True)
        if telegram_account
        else None,
        **user.model_dump(),
    )


def send_response_approved(
    user: models.UserRead,
    order: schemas.OrderReadSystem,
    response: models.ResponseRead,
    text: str,
) -> None:
    service.send_user_notification(
        models.NotificationSendUser(
            type=models.NotificationType.ORDER_RESPONSE_APPROVE,
            user=user,
            data={"order": order, "response": response, "text": text},
        )
    )


def send_response_declined(user: models.UserRead, order_id: str) -> None:
    service.send_user_notification(
        models.NotificationSendUser(
            type=models.NotificationType.ORDER_RESPONSE_DECLINE,
            user=user,
            data={"order_id": order_id},
        )
    )


def send_logged_notify(user: models.UserReadWithAccounts) -> None:
    service.send_system_notification(
        models.NotificationSendSystem(type=models.NotificationType.LOGGED_NOTIFY, data={"user": user}),
    )


def send_registered_notify(user: models.UserReadWithAccounts) -> None:
    service.send_system_notification(
        models.NotificationSendSystem(type=models.NotificationType.REGISTERED_NOTIFY, data={"user": user}),
    )


def send_verified_notify(user: models.UserReadWithAccounts) -> None:
    service.send_user_notification(models.NotificationSendUser(type=models.NotificationType.VERIFIED_NOTIFY, user=user))


def send_request_verify(user: models.UserReadWithAccounts) -> None:
    service.send_system_notification(
        models.NotificationSendSystem(type=models.NotificationType.REQUEST_VERIFY, data={"user": user})
    )


def send_order_close_notify(user: models.UserRead, order_id: str, url: str, message: str) -> None:
    service.send_system_notification(
        models.NotificationSendSystem(
            type=models.NotificationType.ORDER_CLOSE_REQUEST,
            data={"user": user, "order_id": order_id, "url": url, "message": message},
        )
    )


def send_sent_order_notify(order_id: str, payload: models.MessageCallback) -> None:
    service.send_system_notification(
        models.NotificationSendSystem(
            type=models.NotificationType.ORDER_SENT_NOTIFY,
            data={"order_id": order_id, "payload": payload},
        )
    )


def send_edited_order_notify(order_id: str, payload: models.MessageCallback) -> None:
    service.send_system_notification(
        models.NotificationSendSystem(
            type=models.NotificationType.ORDER_EDITED_NOTIFY,
            data={"order_id": order_id, "payload": payload},
        )
    )


def send_deleted_order_notify(order_id: str, payload: models.MessageCallback) -> None:
    service.send_system_notification(
        models.NotificationSendSystem(
            type=models.NotificationType.ORDER_DELETED_NOTIFY,
            data={"order_id": order_id, "payload": payload},
        )
    )


def send_response_chose_notify(order_id: str, user: models.UserReadWithAccounts, responses: int) -> None:
    service.send_system_notification(
        models.NotificationSendSystem(
            type=models.NotificationType.RESPONSE_CHOSE_NOTIFY,
            data={"order_id": order_id, "user": user, "responses": responses},
        )
    )


def send_order_paid_notify(order: schemas.OrderReadSystem, user: models.UserRead) -> None:
    service.send_system_notification(
        models.NotificationSendSystem(
            type=models.NotificationType.ORDER_PAID_NOTIFY,
            data={"order": order, "user": user},
        )
    )
