import asyncio

from src.core import config, enums
from src.services.auth import models as auth_models
from src.services.integrations.message import models as message_models
from src.services.integrations.bots.service import request as service_request
from src.services.order import schemas as order_schemas
from src.services.response import models as response_models

integration = enums.Integration.telegram


def create_task(func):
    if config.app.telegram_integration:
        asyncio.create_task(func)


def send_order_response_admin(
    order: order_schemas.OrderReadSystem,
    user: auth_models.UserRead,
    text: str,
    is_preorder: bool,
) -> None:
    if is_preorder:
        data = {"preorder": order, "user": user, "text": text, "is_preorder": True}
    else:
        data = {"order": order, "user": user, "text": text, "is_preorder": False}
    create_task(service_request(integration, "message/order_admins", "POST", data=data))


def send_response_approve(
        user: auth_models.UserRead,
        order: order_schemas.OrderReadSystem,
        response: response_models.ResponseRead,
        text: str,
) -> None:
    data = {"order": order, "user": user, "response": response, "text": text}
    create_task(service_request(integration,"message/user_resp_approved_notify", "POST", data=data))


def send_response_decline(user: auth_models.UserRead, order_id: str) -> None:
    data = {"order_id": order_id, "user": user}
    create_task(service_request(integration,"message/user_resp_declined_notify", "POST", data=data))


def send_logged_notify(user: auth_models.UserRead) -> None:
    create_task(service_request(integration,"message/logged_notify", "POST", data=user))


def send_registered_notify(user: auth_models.UserRead) -> None:
    create_task(service_request(integration,"message/registered_notify", "POST", data=user))


def send_request_verify(user: auth_models.UserRead, token: str) -> None:
    data = {"user": user, "token": token}
    create_task(service_request(integration,"message/request_verify_notify", "POST", data=data))


def send_verified_notify(user: auth_models.UserRead) -> None:
    create_task(service_request(integration,"message/verified_notify", "POST", data=user))


def send_order_close_notify(user: auth_models.UserRead, order_id: str, url: str, message: str) -> None:
    data = {"user": user, "order_id": order_id, "url": url, "message": message}
    create_task(service_request(integration,"message/order_close_request_notify", "POST", data=data))


def send_sent_order_notify(order_id: str, payload: message_models.OrderResponse) -> None:
    data = {"order_id": order_id, "pull_payload": payload}
    create_task(service_request(integration,"message/order_sent_notify", "POST", data=data))


def send_edited_order_notify(order_id: str, payload: message_models.OrderResponse) -> None:
    data = {"order_id": order_id, "pull_payload": payload}
    create_task(service_request(integration,"message/order_edited_notify", "POST", data=data))


def send_deleted_order_notify(order_id: str, payload: message_models.OrderResponse) -> None:
    data = {"order_id": order_id, "pull_payload": payload}
    create_task(service_request(integration,"message/order_deleted_notify", "POST", data=data))


def send_response_chose_notify(order_id: str, user: auth_models.UserRead, responses: int) -> None:
    data = {"order_id": order_id, "user": user, "responses": responses}
    create_task(service_request(integration,"message/response_chose_notify", "POST", data=data))


def send_order_paid_notify(order: order_schemas.OrderReadSystem, user: auth_models.UserRead) -> None:
    data = {"order": order, "user": user}
    create_task(service_request(integration,"message/order_paid_notify", "POST", data=data))
