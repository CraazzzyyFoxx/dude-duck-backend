import asyncio

from beanie import PydanticObjectId

from app.services.auth import models as auth_models
from app.services.orders import schemas as order_schemas
from app.services.preorders import models as preorder_models
from app.services.response import models as response_models
from app.services.telegram.service import request as service_request

from . import models


async def order_create(
    order: order_schemas.OrderReadSystem | preorder_models.PreOrderReadSystem,
    categories: list[str],
    configs: list[str],
    *,
    is_pre: bool = False,
    is_gold: bool = False,
) -> models.OrderResponse:
    data = {"order": order, "categories": categories, "configs": configs, "is_gold": is_gold}
    if is_pre:
        resp = await service_request("message/order_create", "POST", data=data)
    else:
        resp = await service_request("message/preorder_create", "POST", data=data)
    return models.OrderResponse.model_validate(resp.json())


async def order_edit(
    order: order_schemas.OrderReadSystem | preorder_models.PreOrderReadSystem,
    configs: list[str],
    *,
    is_pre: bool = False,
    is_gold: bool = False,
) -> models.OrderResponse:
    data = {"order": order, "configs": configs, "is_gold": is_gold}
    if is_pre:
        resp = await service_request("message/order_update", "POST", data=data)
    else:
        resp = await service_request("message/preorder_update", "POST", data=data)
    return models.OrderResponse.model_validate(resp.json())


async def order_delete(
    order: order_schemas.OrderReadSystem | preorder_models.PreOrderReadSystem, pre: bool = False
) -> models.OrderResponse:
    if pre:
        resp = await service_request("message/order_delete", "POST", data=order)
    else:
        resp = await service_request("message/preorder_delete", "POST", data=order)
    return models.OrderResponse.model_validate(resp.json())


def send_preorder_response_admin(
    order: preorder_models.PreOrderReadSystem,
    user: auth_models.UserRead,
    response: response_models.ResponseRead,
) -> None:
    data = {"preorder": order, "user": user, "response": response, "is_preorder": True}
    asyncio.create_task(service_request("message/order_admins", "POST", data=data))


def send_order_response_admin(
    order: order_schemas.OrderReadSystem,
    user: auth_models.UserRead,
    response: response_models.ResponseRead,
) -> None:
    data = {"preorder": order, "user": user, "response": response, "is_preorder": False}
    asyncio.create_task(service_request("message/order_admins", "POST", data=data))


def send_response_approve(
    user: auth_models.UserRead, order_id: PydanticObjectId, response: response_models.ResponseRead
) -> None:
    data = {"order_id": str(order_id), "user": user, "response": response}
    asyncio.create_task(service_request("message/user_resp_approved_notify", "POST", data=data))


def send_response_decline(user: auth_models.UserRead, order_id: str) -> None:
    data = {"order_id": order_id, "user": user}
    asyncio.create_task(service_request("message/user_resp_declined_notify", "POST", data=data))


def send_logged_notify(user: auth_models.UserRead) -> None:
    asyncio.create_task(service_request("message/logged_notify", "POST", data=user))


def send_registered_notify(user: auth_models.UserRead) -> None:
    asyncio.create_task(service_request("message/registered_notify", "POST", data=user))


def send_request_verify(user: auth_models.UserRead, token: str) -> None:
    data = {"user": user, "token": token}
    asyncio.create_task(service_request("message/request_verify_notify", "POST", data=data))


def send_verified_notify(user: auth_models.UserRead) -> None:
    asyncio.create_task(service_request("message/verified_notify", "POST", data=user))


def send_order_close_notify(user: auth_models.UserRead, order_id: str, url: str, message: str) -> None:
    data = {"user": user, "order_id": order_id, "url": url, "message": message}
    asyncio.create_task(service_request("message/order_close_request_notify", "POST", data=data))


def send_sent_order_notify(order_id: str, payload: models.OrderResponse) -> None:
    data = {"order_id": order_id, "pull_payload": payload}
    asyncio.create_task(service_request("message/order_sent_notify", "POST", data=data))


def send_edited_order_notify(order_id: str, payload: models.OrderResponse) -> None:
    data = {"order_id": order_id, "pull_payload": payload}
    asyncio.create_task(service_request("message/order_edited_notify", "POST", data=data))


def send_deleted_order_notify(order_id: str, payload: models.OrderResponse) -> None:
    data = {"order_id": order_id, "pull_payload": payload}
    asyncio.create_task(service_request("message/order_deleted_notify", "POST", data=data))


def send_response_chose_notify(order_id: str, user: auth_models.UserRead, responses: int) -> None:
    data = {"order_id": order_id, "user": user, "responses": responses}
    asyncio.create_task(service_request("message/response_chose_notify", "POST", data=data))


def send_order_paid_notify(order: order_schemas.OrderReadSystem, user: auth_models.UserRead) -> None:
    data = {"order": order, "user": user}
    asyncio.create_task(service_request("message/order_paid_notify", "POST", data=data))
