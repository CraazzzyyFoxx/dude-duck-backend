from httpx import AsyncClient, Limits, TimeoutException, HTTPError
from fastapi.encoders import jsonable_encoder
from loguru import logger
from pydantic import HttpUrl

from app.core import config

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

    async def request(self, data: models.MessageEvent) -> dict | None:
        try:
            response = await self._client.request(
                method="post",
                url=f"{config.app.frontend_url}/api/message",
                json=jsonable_encoder(data, by_alias=False),
                headers={"Authorization": "Bearer " + config.app.frontend_token}
            )
            if response.status_code in [200, 201]:
                return response.json()
            return None
        except TimeoutException as err:
            logger.exception(err)
        except HTTPError as err:
            logger.exception(err)


MessageService = MessageServiceMeta()


async def pull_create(order: models.Order, categories: list[str], configs: list[str]) -> list[models.OrderMessage]:
    data = models.MessageEvent(type=models.MessageEnum.SEND_ORDER,
                               payload=models.MessageEventPayload(order=order, categories=categories,
                                                                  configs=configs))
    resp = await MessageService.request(data=data)
    if resp is None:
        return []
    return [models.OrderMessage.model_validate(r) for r in resp]


async def pull_edit(order: models.Order, configs: list[str]) -> list[models.OrderMessage]:
    data = models.MessageEvent(type=models.MessageEnum.EDIT_ORDER,
                               payload=models.MessageEventPayload(order=order, configs=configs))
    resp = await MessageService.request(data=data)
    return [models.OrderMessage.model_validate(r) for r in resp]


async def pull_delete(order: models.Order):
    data = models.MessageEvent(type=models.MessageEnum.DELETE_ORDER,
                               payload=models.MessageEventPayload(order=order))
    resp = await MessageService.request(data=data)
    return [models.OrderMessage.model_validate(r) for r in resp]


async def send_response_admin_message(order: models.Order, user: models.User, response: models.OrderResponseRead):
    data = models.MessageEvent(type=models.MessageEnum.MESSAGE_RESPONSE,
                               payload=models.MessageEventPayload(order=order, user=user, response=response))
    return await MessageService.request(data=data)


async def pull_send_response_approve(user: models.User, order: models.Order):
    data = models.MessageEvent(type=models.MessageEnum.RESPONSE_APPROVED,
                               payload=models.MessageEventPayload(order=order, user=user))
    return await MessageService.request(data=data)


async def pull_send_response_decline(user: models.User, order: models.Order):
    data = models.MessageEvent(type=models.MessageEnum.RESPONSE_DECLINED,
                               payload=models.MessageEventPayload(order=order, user=user))
    return await MessageService.request(data=data)


async def send_request_verify(user: models.User, token: str):
    data = models.MessageEvent(type=models.MessageEnum.REQUEST_VERIFY,
                               payload=models.MessageEventPayload(user=user, token=token))
    return await MessageService.request(data=data)


async def send_request_verified(user: models.User):
    data = models.MessageEvent(type=models.MessageEnum.VERIFIED, payload=models.MessageEventPayload(user=user))
    return await MessageService.request(data=data)


async def send_order_close_request(user: models.User, order: models.Order, url: HttpUrl, message: str):
    data = models.MessageEvent(type=models.MessageEnum.REQUEST_CLOSE_ORDER,
                               payload=models.MessageEventPayload(user=user, url=url, message=message, order=order))
    return await MessageService.request(data=data)
