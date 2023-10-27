from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from src.core import errors

from . import models

CACHE: dict[int, models.Settings] = {}


async def get(session: AsyncSession) -> models.Settings:
    if CACHE.get(0):
        return CACHE[0]
    result = await session.scalars(sa.select(models.Settings))
    settings = result.one_or_none()
    CACHE[0] = settings  # type: ignore
    return settings  # type: ignore


async def create(session: AsyncSession) -> models.Settings:
    if await get(session) is None:
        settings = models.Settings(api_layer_currency=[])
        session.add(settings)
        await session.commit()
    CACHE.clear()
    return await get(session)


async def update(session: AsyncSession, settings_in: models.SettingsUpdate) -> models.Settings:
    settings = await get(session)
    update_data = settings_in.model_dump(exclude_defaults=True, mode="json")
    query = sa.update(models.Settings).where(models.Settings.id == settings.id).values(**update_data)
    result = await session.scalars(query)
    CACHE.clear()
    return result.first()  # noqa


async def add_token(session: AsyncSession, token: str) -> models.Settings:
    settings = await get(session)
    tokens = list(settings.api_layer_currency)
    for token_db in tokens:
        if token_db["token"] == token:
            raise errors.DDHTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=[errors.DDException(msg="This token already exists", code="already_exist")],
            )

    model = models.ApiLayerCurrencyToken(token=token, uses=1, last_use=datetime.utcnow())
    tokens.append(model.model_dump(mode="json"))
    settings.api_layer_currency = tokens
    session.add(settings)
    await session.commit()
    CACHE.clear()
    return settings


async def remove_token(session: AsyncSession, token: str) -> models.Settings:
    settings = await get(session)
    x = None
    tokens = list(settings.api_layer_currency)
    for token_db in tokens:
        if token_db["token"] == token:
            x = token_db
    if x is None:
        raise errors.DDHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[errors.DDException(msg="Token not found", code="not_exist")],
        )
    tokens.remove(x)
    settings.api_layer_currency = tokens
    session.add(settings)
    await session.commit()
    CACHE.clear()
    return settings
