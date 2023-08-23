from fastapi.encoders import jsonable_encoder
from httpx import Limits, AsyncClient, TimeoutException, HTTPError
from loguru import logger

from app.core import config


class ChannelServiceMeta:
    __slots__ = ("client",)

    def __init__(self):
        self.client = self._build_client()

    @staticmethod
    def _build_client() -> AsyncClient:
        limits = Limits(max_connections=20, max_keepalive_connections=10)
        return AsyncClient(limits=limits, http1=True, verify=False)

    async def init(self) -> None:
        if self.client.is_closed:
            self.client = self._build_client()

    async def shutdown(self) -> None:
        if self.client.is_closed:
            logger.debug("This HTTPXRequest is already shut down. Returning.")
            return
        await self.client.aclose()


ChannelService = ChannelServiceMeta()


async def request(
        endpoint: str,
        method: str,
        data: dict | None = None):
    try:
        response = await ChannelService.client.request(
            method=method,
            url=f"{config.app.frontend_url}/api/{endpoint}",
            json=jsonable_encoder(data),
            headers={"Authorization": "Bearer " + config.app.frontend_token}
        )
        return response
    except TimeoutException as err:
        logger.exception(err)
    except HTTPError as err:
        logger.exception(err)