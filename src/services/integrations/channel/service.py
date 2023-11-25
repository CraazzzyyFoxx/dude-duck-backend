import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from src.core import enums

from . import models


async def get(session: AsyncSession, channel_id: int) -> models.Channel | None:
    query = sa.select(models.Channel).where(models.Channel.channel_id == channel_id)
    result = await session.execute(query)
    return result.scalars().first()


async def create(session: AsyncSession, channel_in: models.ChannelCreate) -> models.Channel:
    channel_db = models.Channel(**channel_in.model_dump())
    session.add(channel_db)
    await session.commit()
    return channel_db


async def update(session: AsyncSession, channel: models.Channel, channel_in: models.ChannelUpdate) -> models.Channel:
    channel_data = channel_in.model_dump(exclude_unset=True, exclude_none=True)
    for field, value in channel_data.items():
        setattr(channel, field, value)
    session.add(channel)
    await session.commit()
    return channel


async def delete(session: AsyncSession, channel_id: int) -> None:
    channel = await get(session, channel_id)
    if channel:
        await session.delete(channel)
        await session.commit()


async def get_by_game_category(
    session: AsyncSession, integration: enums.Integration, game: str, category: str | None = None
) -> models.Channel | None:
    query = (
        sa.select(models.Channel)
        .where(models.Channel.game == game, models.Channel.category == category)
        .where(models.Channel.integration == integration)
    )
    result = await session.execute(query)
    return result.scalars().first()


async def get_by_game_categories(
    session: AsyncSession, integration: enums.Integration, game: str, categories: list[str]
) -> list[models.Channel]:
    query = (
        sa.select(models.Channel)
        .where(models.Channel.game == game, models.Channel.category.in_(categories))
        .where(models.Channel.integration == integration)
    )
    result = await session.execute(query)
    return result.scalars().all()  # type: ignore
