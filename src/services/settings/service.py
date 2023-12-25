import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from src import models

CACHE: dict[int, models.Settings] = {}


async def get(session: AsyncSession) -> models.Settings:
    if CACHE.get(0):
        return CACHE[0]
    result = await session.scalars(sa.select(models.Settings))
    settings = result.one_or_none()
    CACHE[0] = settings
    return settings  # type: ignore


async def create(session: AsyncSession) -> models.Settings:
    if await get(session) is None:
        settings = models.Settings()
        session.add(settings)
        await session.commit()
    CACHE.clear()
    return await get(session)


async def update(session: AsyncSession, settings_in: models.SettingsUpdate) -> models.Settings:
    settings = await get(session)
    update_data = settings_in.model_dump(exclude_defaults=True, mode="json")
    query = (
        sa.update(models.Settings)
        .where(models.Settings.id == settings.id)
        .values(**update_data)
        .returning(models.Settings)
    )
    result = await session.scalars(query)
    await session.commit()
    CACHE.clear()
    return result.one()
