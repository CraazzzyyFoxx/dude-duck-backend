import httpx
from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder
from httpx import HTTPError, TimeoutException
from loguru import logger

from app.core import config


class TelegramServiceMeta:
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


TelegramService = TelegramServiceMeta()


async def request(
        endpoint: str,
        method: str,
        data: dict | None = None
) -> httpx.Response:
    try:
        response = await TelegramService.client.request(
            method=method,
            url=f"{config.app.frontend_url}/api/{endpoint}",
            json=jsonable_encoder(data),
            headers={"Authorization": "Bearer " + config.app.frontend_token}
        )
    except TimeoutException as err:
        logger.exception(err)
        raise HTTPException(status_code=500, detail=[
            {"msg": "Couldn't communicate with Telegram Bot (HTTP 503 error) : Service Unavailable"}
        ])
    except HTTPError as err:
        logger.exception(err)
        raise HTTPException(status_code=500, detail=[
            {"msg": "Couldn't communicate with Telegram Bot (HTTP 503 error) : Service Unavailable"}
        ])
    else:
        if response.status_code not in (200, 201, 404):
            raise HTTPException(status_code=500, detail=[
                {"msg": "Couldn't communicate with Telegram Bot (HTTP 503 error) : Service Unavailable"}
            ])
        return response
