import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from src import models
from src.core import errors, pagination

from . import service


async def get(session: AsyncSession, channel_id: int) -> models.Channel:
    channel = await service.get(session, channel_id)
    if not channel:
        raise errors.ApiHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[errors.ApiException(msg="A channel with this id does not exist.", code="not_found")],
        )
    return channel


async def create(session: AsyncSession, channel_in: models.ChannelCreate) -> models.Channel:
    channel = await service.get_by_game_category(session, channel_in.integration, channel_in.game, channel_in.category)
    if channel:
        raise errors.ApiHTTPException(
            status_code=400,
            detail=[
                errors.ApiException(
                    msg="A channel with this game and category already exists.",
                    code="already_exists",
                )
            ],
        )
    channel = await service.create(session, channel_in)
    return channel


async def delete(session: AsyncSession, channel_id: int):
    channel = await get(session, channel_id)
    await service.delete(session, channel_id)
    return channel


async def get_by_filter(
    session: AsyncSession, params: models.ChannelPaginationParams
) -> pagination.Paginated[models.ChannelRead]:
    query = params.apply_filter(sa.select(models.Channel))
    result = await session.execute(params.apply_pagination(query))
    results = [models.ChannelRead.model_validate(channel, from_attributes=True) for channel in result.scalars().all()]
    total = await session.scalars(params.apply_filter(sa.select(sa.func.count(models.Channel.id))))
    return pagination.Paginated(results=results, total=total.one(), page=params.page, per_page=params.per_page)
