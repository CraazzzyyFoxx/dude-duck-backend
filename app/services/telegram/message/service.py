import typing
import asyncio

from app.services.preorders import models as preorder_models
from app.services.orders import schemas as order_schemas
from app.services.auth import models as auth_models
from app.services.response import models as response_models

from app.services.telegram.service import request as service_request

from . import models


async def request(data: dict):
    return await service_request("message", "post", data)


@typing.overload
def build_payload(
        type: models.MessageEnum,
        *,
        order: order_schemas.OrderReadUser | None = None,
        preorder: preorder_models.PreOrderRead | None = None,
        categories: list[str] | None = None,
        configs: list[str] | None = None,
        is_preorder: bool | None = None,
        user: auth_models.User | None = None,
        response: response_models.Response | None = None,
        token: str | None = None,
        url: str | None = None,
        message: str | None = None,
        payload: models.OrderResponse | None = None,
        total: int | None = None,
) -> dict:
    pass


def build_payload(
        type: models.MessageEnum,
        **kwargs,
) -> dict:
    payload = {}
    kwargs["order"] = kwargs["order"] if kwargs.get("order") else None
    kwargs["preorder"] = kwargs["preorder"] if kwargs.get("preorder") else None
    kwargs["user"] = auth_models.UserRead(**kwargs["user"].model_dump()) if kwargs.get("user") else None
    if kwargs.get("response"):
        kwargs["response"] = response_models.ResponseRead(**kwargs["response"].model_dump())
    for kwarg in kwargs:
        if kwargs.get(kwarg) is not None:
            payload[kwarg] = kwargs[kwarg]
    return {"type": type.value, "payload": kwargs}


async def pull_order_create(
        order: order_schemas.OrderReadUser,
        categories: list[str],
        configs: list[str]
) -> models.OrderResponse:
    data = build_payload(type=models.MessageEnum.SEND_ORDER, order=order, categories=categories, configs=configs)
    return models.OrderResponse.model_validate((await request(data=data)).json())


async def pull_order_edit(
        order: order_schemas.OrderReadUser,
        configs: list[str]
) -> models.OrderResponse:
    data = build_payload(type=models.MessageEnum.EDIT_ORDER, order=order, configs=configs)
    return models.OrderResponse.model_validate((await request(data=data)).json())


async def pull_order_delete(
        order: order_schemas.OrderReadUser,
) -> models.OrderResponse:
    data = build_payload(type=models.MessageEnum.DELETE_ORDER, order=order)
    return models.OrderResponse.model_validate((await request(data=data)).json())


async def pull_preorder_create(
        order: preorder_models.PreOrderRead,
        categories: list[str],
        configs: list[str]
) -> models.OrderResponse:
    data = build_payload(type=models.MessageEnum.SEND_PREORDER, preorder=order, categories=categories,
                         configs=configs)
    return models.OrderResponse.model_validate((await request(data=data)).json())


async def pull_preorder_edit(
        order: preorder_models.PreOrderRead,
        configs: list[str]
) -> models.OrderResponse:
    data = build_payload(type=models.MessageEnum.EDIT_PREORDER, preorder=order, configs=configs)
    return models.OrderResponse.model_validate((await request(data=data)).json())


async def pull_preorder_delete(
        order: preorder_models.PreOrderRead
) -> models.OrderResponse:
    data = build_payload(type=models.MessageEnum.DELETE_PREORDER, preorder=order)
    return models.OrderResponse.model_validate((await request(data=data)).json())


def send_preorder_response_admin(
        order: preorder_models.PreOrderRead,
        user: auth_models.User,
        response: response_models.Response
):
    data = build_payload(
        type=models.MessageEnum.RESPONSE_ORDER_ADMINS,
        preorder=order,
        user=user,
        response=response,
        is_preorder=True
    )
    asyncio.create_task(request(data))


def send_response_admin(
        order: order_schemas.OrderReadUser,
        user: auth_models.User,
        response: response_models.Response
):
    data = build_payload(
        type=models.MessageEnum.RESPONSE_ORDER_ADMINS,
        order=order,
        user=user, response=response,
        is_preorder=False
    )

    asyncio.create_task(request(data))


def send_response_approve(
        user: auth_models.User,
        order: order_schemas.OrderReadUser,
        response: response_models.Response
):
    data = build_payload(type=models.MessageEnum.RESPONSE_ORDER_APPROVED, order=order, user=user, response=response)
    asyncio.create_task(request(data))


def send_response_decline(
        user: auth_models.User,
        order: order_schemas.OrderReadUser
):
    data = build_payload(type=models.MessageEnum.RESPONSE_ORDER_DECLINED, order=order, user=user)
    asyncio.create_task(request(data))


def send_request_verify(
        user: auth_models.User,
        token: str
):
    data = build_payload(type=models.MessageEnum.REQUEST_VERIFY, user=user, token=token)
    asyncio.create_task(request(data))


def send_verified_notify(
        user: auth_models.User
):
    data = build_payload(type=models.MessageEnum.VERIFIED, user=user)
    asyncio.create_task(request(data))


def send_order_close_notify(
        user: auth_models.User,
        order: order_schemas.OrderReadUser,
        url: str,
        message: str
):
    data = build_payload(type=models.MessageEnum.REQUEST_CLOSE_ORDER, user=user, order=order, url=url, message=message)
    asyncio.create_task(request(data))


def send_logged_notify(
        user: auth_models.User
):
    data = build_payload(type=models.MessageEnum.LOGGED, user=user)
    asyncio.create_task(request(data))


def send_registered_notify(
        user: auth_models.User
):
    data = build_payload(type=models.MessageEnum.REGISTERED, user=user)
    asyncio.create_task(request(data))


def send_sent_order_notify(
        order: order_schemas.OrderReadUser,
        payload: models.OrderResponse
):
    data = build_payload(type=models.MessageEnum.SENT_ORDER, order=order, payload=payload)
    asyncio.create_task(request(data))


def send_edited_order_notify(
        order: order_schemas.OrderReadUser,
        payload: models.OrderResponse
):
    data = build_payload(type=models.MessageEnum.EDITED_ORDER, order=order, payload=payload)
    asyncio.create_task(request(data))


def send_deleted_order_notify(
        order: order_schemas.OrderReadUser,
        payload: models.OrderResponse
):
    data = build_payload(type=models.MessageEnum.DELETED_ORDER, order=order, payload=payload)
    asyncio.create_task(request(data))


def send_response_chose_notify(
        order: order_schemas.OrderReadUser,
        user: auth_models.User,
        total: int
):
    data = build_payload(type=models.MessageEnum.RESPONSE_CHOSE, order=order, user=user, total=total)
    asyncio.create_task(request(data))


def send_order_paid_notify(
        order: order_schemas.OrderReadUser,
        user: auth_models.User
):
    data = build_payload(type=models.MessageEnum.ORDER_PAID, order=order, user=user)
    asyncio.create_task(request(data))
