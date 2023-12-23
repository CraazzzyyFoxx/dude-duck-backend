import httpx
import sqlalchemy as sa
from fastapi.encoders import jsonable_encoder
from httpx import ConnectError, HTTPError, TimeoutException
from loguru import logger
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src import models
from src.core import config, errors

telegram_client = httpx.AsyncClient(
    verify=False,
    base_url=config.app.telegram_url,
    headers={"Authorization": "Bearer " + config.app.telegram_token},
)


error = errors.ApiHTTPException(
    status_code=500,
    detail=[
        errors.ApiException(
            msg="Couldn't communicate with Telegram Bot (HTTP 503 error) : Service Unavailable",
            code="internal_error",
        )
    ],
)


async def request(endpoint: str, method: str, data: dict | list | BaseModel | None = None) -> httpx.Response:
    try:
        response = await telegram_client.request(
            method=method,
            url=f"api/{endpoint}",
            json=jsonable_encoder(data),
        )
        if response.status_code not in (200, 201, 404):
            logger.error(response.json())
            raise error from None
        logger.info(response.json())
        return response
    except (TimeoutException, HTTPError, ConnectError):
        raise error from None


async def get_tg_account(session: AsyncSession, user_id: int) -> models.TelegramAccount | None:
    query = sa.select(models.TelegramAccount).where(models.TelegramAccount.user_id == user_id)
    account = await session.execute(query)
    return account.scalars().first()


async def connect_telegram(
    session: AsyncSession, user: models.User, payload: models.TelegramAccountCreate
) -> models.TelegramAccount:
    query = (
        sa.insert(models.TelegramAccount)
        .values(user_id=user.id, **payload.model_dump())
        .returning(models.TelegramAccount)
    )
    try:
        result = await session.execute(query)
        await session.commit()
    except IntegrityError as e:
        raise errors.ApiHTTPException(
            status_code=400,
            detail=[errors.ApiException(code="already_exists", msg="Telegram account already exists")],
        ) from e

    return result.scalars().one()


async def disconnect_telegram(session: AsyncSession, user: models.User) -> models.TelegramAccount:
    account = await get_tg_account(session, user.id)
    if account is None:
        raise errors.ApiHTTPException(
            status_code=400,
            detail=[errors.ApiException(code="not_found", msg="Telegram account not found")],
        )
    await session.delete(account)
    await session.commit()
    return account
