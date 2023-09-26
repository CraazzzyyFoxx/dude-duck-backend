import httpx
from fastapi.encoders import jsonable_encoder
from httpx import HTTPError, TimeoutException
from loguru import logger

from app.core import config, errors


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


async def request(endpoint: str, method: str, data: dict | None = None) -> httpx.Response:
    if config.app.telegram_integration is False:
        raise errors.DudeDuckHTTPException(
            status_code=500,
            detail=[errors.DudeDuckException(msg="Telegram Bot integration disabled", code="disabled")],
        ) from None

    try:
        response = await TelegramService.client.request(
            method=method,
            url=f"{config.app.telegram_url}/api/{endpoint}",
            json=jsonable_encoder(data),
            headers={"Authorization": "Bearer " + config.app.telegram_token},
        )
    except TimeoutException as err:
        logger.exception(err)
        raise errors.DudeDuckHTTPException(
            status_code=500,
            detail=[
                errors.DudeDuckException(
                    msg="Couldn't communicate with Telegram Bot (HTTP 503 error) : Service Unavailable",
                    code="internal_error",
                )
            ],
        ) from None
    except HTTPError as err:
        logger.exception(err)
        raise errors.DudeDuckHTTPException(
            status_code=500,
            detail=[
                errors.DudeDuckException(
                    msg="Couldn't communicate with Telegram Bot (HTTP 503 error) : Service Unavailable",
                    code="internal_error",
                )
            ],
        ) from None
    else:
        if response.status_code not in (200, 201, 404):
            raise errors.DudeDuckHTTPException(
                status_code=500,
                detail=[
                    errors.DudeDuckException(
                        msg="Couldn't communicate with Telegram Bot (HTTP 503 error) : Service Unavailable",
                        code="internal_error",
                    )
                ],
            ) from None
        logger.info(response.json())
        return response
