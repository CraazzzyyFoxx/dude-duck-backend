import asyncio
import typing

from beanie import PydanticObjectId
from httpx import Response

from app.services.auth import models as auth_models
from app.services.orders import schemas as order_schemas
from app.services.preorders import models as preorder_models
from app.services.response import models as response_models
from app.services.telegram.service import request as service_request

from . import models


async def request(data: dict) -> Response:
    return await service_request("message", "post", data)


@typing.overload
def build_payload(
    message_type: models.MessageEnum,
    *,
    order_id: str | None = None,
    order: order_schemas.OrderReadSystem | None = None,
    preorder: preorder_models.PreOrderReadSystem | None = None,
    pull_payload: models.OrderResponse | None = None,
    categories: list[str] | None = None,
    configs: list[str] | None = None,
    is_preorder: bool | None = None,
    user: auth_models.UserRead | None = None,
    token: str | None = None,
    response: response_models.ResponseRead | None = None,
    responses: int | None = None,
    url: str | None = None,
    message: str | None = None,
) -> dict:
    pass


def build_payload(
    message_type: models.MessageEnum,
    **kwargs,
) -> dict:
    payload = {}
    for kwarg in kwargs:
        if kwargs.get(kwarg) is not None:
            payload[kwarg] = kwargs[kwarg]
    return {"type": message_type.value, "payload": kwargs}


async def pull_order_create(
    order: order_schemas.OrderReadSystem | preorder_models.PreOrderReadSystem,
    categories: list[str],
    configs: list[str],
    pre: bool = False,
) -> models.OrderResponse:
    data = build_payload(
        message_type=models.MessageEnum.SEND_ORDER if not pre else models.MessageEnum.SEND_PREORDER,
        order=order,
        categories=categories,
        configs=configs,
    )
    return models.OrderResponse.model_validate((await request(data=data)).json())


async def pull_order_edit(
    order: order_schemas.OrderReadSystem | preorder_models.PreOrderReadSystem,
    configs: list[str],
    pre: bool = False,
) -> models.OrderResponse:
    data = build_payload(
        message_type=models.MessageEnum.EDIT_ORDER if not pre else models.MessageEnum.EDIT_PREORDER,
        order=order,
        configs=configs,
    )
    return models.OrderResponse.model_validate((await request(data=data)).json())


async def pull_order_delete(
    order: order_schemas.OrderReadSystem | preorder_models.PreOrderReadSystem, pre: bool = False
) -> models.OrderResponse:
    data = build_payload(
        message_type=models.MessageEnum.DELETE_ORDER if not pre else models.MessageEnum.DELETE_PREORDER,
        order=order,
    )
    return models.OrderResponse.model_validate((await request(data=data)).json())


def send_preorder_response_admin(
    order: preorder_models.PreOrderReadSystem,
    user: auth_models.UserRead,
    response: response_models.ResponseRead,
) -> None:
    data = build_payload(
        message_type=models.MessageEnum.RESPONSE_ORDER_ADMINS,
        preorder=order,
        user=user,
        response=response,
        is_preorder=True,
    )
    asyncio.create_task(request(data))


def send_response_admin(
    order: order_schemas.OrderReadSystem,
    user: auth_models.UserRead,
    response: response_models.ResponseRead,
) -> None:
    data = build_payload(
        message_type=models.MessageEnum.RESPONSE_ORDER_ADMINS,
        order=order,
        user=user,
        response=response,
        is_preorder=False,
    )

    asyncio.create_task(request(data))


def send_response_approve(
    user: auth_models.UserRead, order_id: PydanticObjectId, response: response_models.ResponseRead
) -> None:
    data = build_payload(
        message_type=models.MessageEnum.RESPONSE_ORDER_APPROVED,
        order_id=str(order_id),
        user=user,
        response=response,
    )
    asyncio.create_task(request(data))


def send_response_decline(user: auth_models.UserRead, order_id: str) -> None:
    data = build_payload(message_type=models.MessageEnum.RESPONSE_ORDER_DECLINED, order_id=order_id, user=user)
    asyncio.create_task(request(data))


def send_request_verify(user: auth_models.UserRead, token: str) -> None:
    data = build_payload(message_type=models.MessageEnum.REQUEST_VERIFY, user=user, token=token)
    asyncio.create_task(request(data))


def send_verified_notify(user: auth_models.UserRead) -> None:
    data = build_payload(message_type=models.MessageEnum.VERIFIED, user=user)
    asyncio.create_task(request(data))


def send_order_close_notify(user: auth_models.UserRead, order_id: str, url: str, message: str) -> None:
    data = build_payload(
        message_type=models.MessageEnum.REQUEST_CLOSE_ORDER,
        user=user,
        order_id=order_id,
        url=url,
        message=message,
    )
    asyncio.create_task(request(data))


def send_logged_notify(user: auth_models.UserRead) -> None:
    data = build_payload(message_type=models.MessageEnum.LOGGED, user=user)
    asyncio.create_task(request(data))


def send_registered_notify(user: auth_models.UserRead) -> None:
    data = build_payload(message_type=models.MessageEnum.REGISTERED, user=user)
    asyncio.create_task(request(data))


def send_sent_order_notify(order_id: str, payload: models.OrderResponse) -> None:
    data = build_payload(message_type=models.MessageEnum.SENT_ORDER, order_id=order_id, pull_payload=payload)
    asyncio.create_task(request(data))


def send_edited_order_notify(order_id: str, payload: models.OrderResponse) -> None:
    data = build_payload(message_type=models.MessageEnum.EDITED_ORDER, order_id=order_id, pull_payload=payload)
    asyncio.create_task(request(data))


def send_deleted_order_notify(order_id: str, payload: models.OrderResponse) -> None:
    data = build_payload(message_type=models.MessageEnum.DELETED_ORDER, order_id=order_id, pull_payload=payload)
    asyncio.create_task(request(data))


def send_response_chose_notify(order_id: str, user: auth_models.UserRead, responses: int) -> None:
    data = build_payload(
        message_type=models.MessageEnum.RESPONSE_CHOSE,
        order_id=order_id,
        user=user,
        responses=responses,
    )
    asyncio.create_task(request(data))


def send_order_paid_notify(order: order_schemas.OrderReadSystem, user: auth_models.UserRead) -> None:
    data = build_payload(message_type=models.MessageEnum.ORDER_PAID, order=order, user=user)
    asyncio.create_task(request(data))
