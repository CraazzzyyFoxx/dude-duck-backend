import typing
from datetime import UTC, datetime

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from src import models


async def get(session: AsyncSession, response_id: int, pre: bool = False) -> models.Response | None:
    result = await session.scalars(
        sa.select(models.Response)
        .where(models.Response.id == response_id, models.Response.is_preorder == pre)
        .options(joinedload(models.Response.user))
    )
    return result.first()


async def create(
    session: AsyncSession, response_in: models.ResponseCreate, is_preorder: bool = False
) -> models.Response:
    response = models.Response(**response_in.model_dump())
    response.is_preorder = is_preorder
    session.add(response)
    await session.commit()
    return response


async def delete(session: AsyncSession, response_id: int, is_preorder: bool = False) -> None:
    response = await get(session, response_id, pre=is_preorder)
    if response:
        await session.delete(response)
        await session.commit()


async def get_by_order_id(
    session: AsyncSession, order_id: int, is_preorder: bool = False
) -> typing.Sequence[models.Response]:
    result = await session.scalars(
        sa.select(models.Response)
        .where(
            models.Response.order_id == order_id,
            models.Response.is_preorder == is_preorder,
        )
        .options(joinedload(models.Response.user))
    )
    return result.all()


async def get_by_user_id(session: AsyncSession, user_id: int, pre: bool = False) -> typing.Sequence[models.Response]:
    result = await session.scalars(
        sa.select(models.Response)
        .where(models.Response.user_id == user_id, models.Response.is_preorder == pre)
        .options(joinedload(models.Response.user))
    )
    return result.all()


async def get_by_order_id_user_id(
    session: AsyncSession, order_id: int, user_id: int, pre: bool = False
) -> models.Response | None:
    result = await session.scalars(
        sa.select(models.Response)
        .where(models.Response.order_id == order_id, models.Response.user_id == user_id)
        .where(models.Response.is_preorder == pre)
        .options(joinedload(models.Response.user))
    )
    return result.first()


async def update(
    session: AsyncSession,
    response: models.Response,
    response_in: models.ResponseUpdate,
    patch: bool = False,
) -> models.Response:
    update_data = response_in.model_dump(exclude_none=True, exclude_defaults=patch)
    if response_in.approved is True and not response.approved:
        update_data["approved_at"] = datetime.now(UTC)
    if response_in.approved is False:
        update_data["approved_at"] = None
    await session.execute(sa.update(models.Response).where(models.Response.id == response.id).values(**update_data))
    await session.commit()
    return response
