import typing
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from . import models


async def get(session: AsyncSession, response_id: int, pre: bool = False) -> models.BaseResponse | None:
    model = models.Response if not pre else models.PreResponse
    result = await session.scalars(sa.select(model).where(model.id == response_id).options(joinedload(model.user)))
    return result.first()


async def create(session: AsyncSession, response_in: models.ResponseCreate, pre: bool = False) -> models.BaseResponse:
    model = models.Response if not pre else models.PreResponse
    response = model(**response_in.model_dump())
    session.add(response)
    await session.commit()
    return response


async def delete(session: AsyncSession, response_id: int, pre: bool = False) -> None:
    response = await get(session, response_id, pre=pre)
    if response:
        await session.delete(response)
        await session.commit()


async def get_by_order_id(
    session: AsyncSession, order_id: int, pre: bool = False
) -> typing.Sequence[models.BaseResponse]:
    model = models.Response if not pre else models.PreResponse
    result = await session.scalars(sa.select(model).where(model.order_id == order_id).options(joinedload(model.user)))
    return result.all()


async def get_by_user_id(
    session: AsyncSession, user_id: int, pre: bool = False
) -> typing.Sequence[models.BaseResponse]:
    model = models.Response if not pre else models.PreResponse
    result = await session.scalars(sa.select(model).where(model.user_id == user_id).options(joinedload(model.user)))
    return result.all()


async def get_by_order_id_user_id(
    session: AsyncSession, order_id: int, user_id: int, pre: bool = False
) -> models.BaseResponse | None:
    model = models.Response if not pre else models.PreResponse
    result = await session.scalars(
        sa.select(model)
        .where(model.order_id == order_id, model.user_id == user_id)
        .options(joinedload(model.user))
    )
    return result.first()


async def get_all(session: AsyncSession, pre: bool = False) -> typing.Sequence[models.BaseResponse]:
    model = models.Response if not pre else models.PreResponse
    result = await session.scalars(sa.select(model))
    return result.all()


async def update(
    session: AsyncSession,
    response: models.BaseResponse,
    response_in: models.ResponseUpdate,
) -> models.BaseResponse:
    update_data = response_in.model_dump()
    if response_in.approved is True and not response.approved:
        update_data["approved_at"] = datetime.utcnow()
    if response_in.approved is False:
        update_data["approved_at"] = None
    await session.execute(sa.update(models.Response).where(models.Response.id == response.id).values(**update_data))
    await session.commit()
    return response


async def patch(
    session: AsyncSession,
    response: models.BaseResponse,
    response_in: models.ResponseUpdate,
) -> models.BaseResponse:
    update_data = response_in.model_dump(exclude_none=True, exclude_defaults=True)
    if response_in.approved is True and not response.approved:
        update_data["approved_at"] = datetime.utcnow()
    if response_in.approved is False:
        update_data["approved_at"] = None
    await session.execute(sa.update(models.Response).where(models.Response.id == response.id).values(**update_data))
    await session.commit()
    return response
