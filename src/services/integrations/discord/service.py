import httpx
from fastapi.encoders import jsonable_encoder
from httpx import ConnectError, HTTPError, TimeoutException
from loguru import logger
from pydantic import BaseModel

from src.core import config, errors

discord_client = httpx.AsyncClient(
    verify=False,
    base_url=config.app.discord_url,
    headers={"Authorization": "Bearer " + config.app.discord_token},
)


error = errors.ApiHTTPException(
    status_code=500,
    detail=[
        errors.ApiException(
            msg="Couldn't communicate with Discord Bot (HTTP 503 error) : Service Unavailable",
            code="internal_error",
        )
    ],
)


async def request(endpoint: str, method: str, data: dict | list | BaseModel | None = None) -> httpx.Response:
    try:
        response = await discord_client.request(
            method=method,
            url=f"api/{endpoint}",
            json=jsonable_encoder(data),
        )
        if response.status_code not in (200, 201, 404):
            logger.error(response.json())
            raise error from None
        return response
    except (TimeoutException, HTTPError, ConnectError):
        raise error from None
