import httpx
from fastapi.encoders import jsonable_encoder
from httpx import ConnectError, HTTPError, TimeoutException
from loguru import logger
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.core import config, errors, enums
from src.services.integrations.message import models as message_models


class BotServiceMeta:
    __slots__ = ("client",)

    def __init__(self) -> None:
        self.client = httpx.AsyncClient(verify=False)

    @staticmethod
    def _build_client() -> httpx.AsyncClient:
        return httpx.AsyncClient()

    async def init(self) -> None:
        if self.client.is_closed:
            self.client = self._build_client()

    async def shutdown(self) -> None:
        if self.client.is_closed:
            logger.debug("This HTTPXRequest is already shut down. Returning.")
            return

        await self.client.aclose()


BotService = BotServiceMeta()


async def request(
        integration: enums.Integration, endpoint: str, method: str, data: dict | list | BaseModel | None = None
) -> httpx.Response:
    url = config.app.telegram_url if integration == enums.Integration.telegram else config.app.discord_url
    error_msg = "Telegram" if integration == enums.Integration.telegram else "Discord"
    try:
        response = await BotService.client.request(
            method=method,
            url=f"{url}/api/{endpoint}",
            json=jsonable_encoder(data),
            headers={"Authorization": "Bearer " + config.app.telegram_token},
        )
        if response.status_code not in (200, 201, 404):
            logger.error(response.json())
            raise errors.ApiHTTPException(
                status_code=500,
                detail=[
                    errors.ApiException(
                        msg=f"Couldn't communicate with {error_msg} Bot (HTTP 503 error) : Service Unavailable",
                        code="internal_error",
                    )
                ],
            ) from None
        return response
    except (TimeoutException, HTTPError, ConnectError) as err:
        raise errors.ApiHTTPException(
            status_code=500,
            detail=[
                errors.ApiException(
                    msg=f"Couldn't communicate with {error_msg} Bot (HTTP 503 error) : Service Unavailable",
                    code="internal_error",
                )
            ],
        ) from None


async def create_message(
    session: AsyncSession,
        integration: enums.Integration,
        messages_in: list[message_models.MessageCreate]
) -> list[tuple[message_models.Message | None, message_models.MessageStatus]]:
    resp: list[tuple[message_models.Message | None, message_models.MessageStatus]] = []
    for message_in in messages_in:
        payload = {
            "channel_id": message_in.channel_id,
            "order_id": message_in.order_id,
            "text": message_in.text,
            "is_preorder": True if message_in.type == message_models.MessageType.PRE_ORDER else False,
        }

        response = await request(integration, "message/order_create", "POST", data=payload)
        data = message_models.OrderResponse.model_validate(response.json())
        for msg in data.created:
            message_db = message_models.Message(
                order_id=message_in.order_id,
                channel_id=msg.channel_id,
                message_id=msg.message_id,
                integration=message_in.integration,
                type=message_in.type,
            )
            session.add(message_db)
            resp.append((message_db, msg.status))
        for msg in data.skipped:
            resp.append((None, msg.status))
    await session.commit()
    return resp


async def update_message(
    session: AsyncSession,
        integration: enums.Integration,
        messages_in: list[tuple[message_models.Message, message_models.MessageUpdate]]
) -> list[tuple[message_models.Message | None, message_models.MessageStatus]]:
    resp: list[tuple[message_models.Message | None, message_models.MessageStatus]] = []
    for msg, message_in in messages_in:
        payload = {
            "message": msg,
            "order_id": msg.order_id,
            "text": message_in.text,
            "is_preorder": True if msg.type == message_models.MessageType.PRE_ORDER else False,
        }

        response = await request(integration, "message/order_update", "POST", data=payload)
        data = message_models.OrderResponse.model_validate(response.json())
        for message in data.updated:
            resp.append((msg, message.status))
        for message in data.skipped:
            if message.status == message_models.MessageStatus.NOT_FOUND:
                await session.delete(msg)
            resp.append((msg, message.status))
    await session.commit()
    return resp


async def delete_message(
    session: AsyncSession, integration: enums.Integration, messages: list[message_models.Message]
) -> list[tuple[message_models.Message | None, message_models.MessageStatus]]:
    resp: list[tuple[message_models.Message | None, message_models.MessageStatus]] = []
    for message in messages:
        json = {
            "message": message,
            "order_id": message.order_id,
        }
        response = await request(integration, "message/order_delete", "POST", data=json)
        data = message_models.OrderResponse.model_validate(response.json())
        for msg in data.deleted:
            await session.delete(message)
            resp.append((message, msg.status))
        for msg in data.skipped:
            if msg.status == message_models.MessageStatus.NOT_FOUND:
                await session.delete(message)
            resp.append((message, msg.status))
    await session.commit()
    return resp
