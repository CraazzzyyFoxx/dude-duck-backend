import typing

import httpx
from httpx import AsyncClient, Limits, TimeoutException, HTTPError
from fastapi.encoders import jsonable_encoder
from loguru import logger
from pydantic import HttpUrl

from app.core import config
from app.services.orders import models as order_models
from app.services.orders import schemas as order_schemas
from app.services.auth import models as auth_models
from app.services.response import models as response_models

from . import models


class MessageServiceMeta:
    __slots__ = ("_client",)

    def __init__(self):
        self._client = self._build_client()

    @staticmethod
    def _build_client() -> AsyncClient:
        limits = Limits(max_connections=20, max_keepalive_connections=10)
        return AsyncClient(limits=limits, http1=True, verify=False)

    async def init(self) -> None:
        if self._client.is_closed:
            self._client = self._build_client()

    async def shutdown(self) -> None:
        if self._client.is_closed:
            logger.debug("This HTTPXRequest is already shut down. Returning.")
            return
        await self._client.aclose()

    async def request(self, data: dict):
        try:
            response = await self._client.request(
                method="post",
                url=f"{config.app.frontend_url}/api/message",
                json=jsonable_encoder(data),
                headers={"Authorization": "Bearer " + config.app.frontend_token}
            )
            return response
        except TimeoutException as err:
            logger.exception(err)
        except HTTPError as err:
            logger.exception(err)


MessageService = MessageServiceMeta()


@typing.overload
def build_payload(
        msg_type: models.MessageEnum,
        *,
        order: order_models.Order | None = None,
        categories: list[str] | None = None,
        configs: list[str] | None = None,
        user: auth_models.User | None = None,
        response: response_models.Response | None = None,
        token: str | None = None,
        url: HttpUrl | None = None,
        message: str | None = None,
        count_channels: int | None = None,
        total: int | None = None,
) -> dict:
    pass


def build_payload(
        msg_type: models.MessageEnum,
        **kwargs,
) -> dict:
    payload = {}
    kwargs["order"] = order_schemas.OrderRead(**kwargs["order"].model_dump()) if kwargs.get(
        "order") else None
    kwargs["user"] = auth_models.UserRead(**kwargs["user"].model_dump()) if kwargs.get(
        "user") else None
    if kwargs.get("response"):
        kwargs["response"] = response_models.ResponseRead.model_validate(kwargs["response"])
    for kwarg in kwargs:
        if kwargs.get(kwarg) is not None:
            payload[kwarg] = kwargs[kwarg]
    return {"type": msg_type.value, "payload": kwargs}


async def pull_create(
        order: order_models.Order,
        categories: list[str],
        configs: list[str]
) -> tuple[httpx.Response, models.OrderResponse | None]:
    data = build_payload(msg_type=models.MessageEnum.SEND_ORDER, order=order, categories=categories, configs=configs)
    resp = await MessageService.request(data=data)
    if resp.status_code == 200:
        return resp, models.OrderResponse.model_validate(resp.json())
    return resp, None


async def pull_edit(
        order: order_models.Order,
        configs: list[str]
) -> tuple[httpx.Response, models.OrderResponse | None]:
    data = build_payload(msg_type=models.MessageEnum.EDIT_ORDER, order=order, configs=configs)
    resp = await MessageService.request(data=data)
    if resp.status_code == 200:
        return resp, models.OrderResponse.model_validate(resp.json())
    return resp, None


async def pull_delete(
        order: order_models.Order
) -> tuple[httpx.Response, models.OrderResponse | None]:
    data = build_payload(msg_type=models.MessageEnum.DELETE_ORDER, order=order)
    resp = await MessageService.request(data=data)
    if resp.status_code == 200:
        return resp, models.OrderResponse.model_validate(resp.json())
    return resp, None


async def send_response_admin(order: order_models.Order, user: auth_models.User, response: response_models.Response):
    data = build_payload(msg_type=models.MessageEnum.RESPONSE_ADMINS, order=order, user=user, response=response)
    await MessageService.request(data=data)


async def send_response_approve(user: auth_models.User, order: order_models.Order, response: response_models.Response):
    data = build_payload(msg_type=models.MessageEnum.RESPONSE_APPROVED, order=order, user=user, response=response)
    await MessageService.request(data=data)


async def send_response_decline(user: auth_models.User, order: order_models.Order):
    data = build_payload(msg_type=models.MessageEnum.RESPONSE_DECLINED, order=order, user=user)
    await MessageService.request(data=data)


async def send_request_verify(user: auth_models.User, token: str):
    data = build_payload(msg_type=models.MessageEnum.REQUEST_VERIFY, user=user, token=token)
    await MessageService.request(data=data)


async def send_verified_notify(user: auth_models.User):
    data = build_payload(msg_type=models.MessageEnum.VERIFIED, user=user)
    await MessageService.request(data=data)


async def send_order_close_notify(user: auth_models.User, order: order_models.Order, url: HttpUrl, message: str):
    data = build_payload(msg_type=models.MessageEnum.REQUEST_CLOSE_ORDER, user=user, order=order, url=url,
                         message=message)
    await MessageService.request(data=data)


async def send_logged_notify(user: auth_models.User):
    data = build_payload(msg_type=models.MessageEnum.LOGGED, user=user)
    await MessageService.request(data=data)


async def send_registered_notify(user: auth_models.User):
    data = build_payload(msg_type=models.MessageEnum.REGISTERED, user=user)
    await MessageService.request(data=data)


async def send_sent_order_notify(order: order_models.Order, count_channels: int):
    data = build_payload(msg_type=models.MessageEnum.SENT_ORDER, order=order, count_channels=count_channels)
    await MessageService.request(data=data)


async def send_edited_order_notify(order: order_models.Order, count_channels: int):
    data = build_payload(msg_type=models.MessageEnum.EDITED_ORDER, order=order, count_channels=count_channels)
    await MessageService.request(data=data)


async def send_deleted_order_notify(order: order_models.Order, count_channels: int):
    data = build_payload(msg_type=models.MessageEnum.DELETED_ORDER, order=order, count_channels=count_channels)
    await MessageService.request(data=data)


async def send_response_chose_notify(order: order_models.Order, user: auth_models.User, total: int):
    data = build_payload(msg_type=models.MessageEnum.RESPONSE_CHOSE, order=order, user=user, total=total)
    await MessageService.request(data=data)


async def send_order_paid_notify(order: order_models.Order, user: auth_models.User):
    data = build_payload(msg_type=models.MessageEnum.ORDER_PAID, order=order, user=user)
    await MessageService.request(data=data)
