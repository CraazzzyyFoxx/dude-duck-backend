import typing

import sqlalchemy as sa
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from src import models


async def get(session: AsyncSession, order_id: int) -> models.PreOrder | None:
    result = await session.scalars(
        sa.select(models.PreOrder)
        .where(models.PreOrder.id == order_id)
        .options(joinedload(models.PreOrder.info), joinedload(models.PreOrder.price))
        .limit(1)
    )
    return result.first()


async def get_all(session: AsyncSession) -> typing.Sequence[models.PreOrder]:
    result = await session.scalars(
        sa.select(models.PreOrder).options(joinedload(models.PreOrder.info), joinedload(models.PreOrder.price))
    )
    return result.all()


async def get_all_by_sheet(session: AsyncSession, spreadsheet: str, sheet: int) -> typing.Sequence[models.PreOrder]:
    result = await session.scalars(
        sa.select(models.PreOrder)
        .where(
            models.PreOrder.spreadsheet == spreadsheet,
            models.PreOrder.sheet_id == sheet,
        )
        .options(joinedload(models.PreOrder.info), joinedload(models.PreOrder.price))
    )
    return result.all()


async def get_all_by_sheet_entity(
    session: AsyncSession, spreadsheet: str, sheet: int, row_id: int
) -> typing.Sequence[models.PreOrder]:
    result = await session.scalars(
        sa.select(models.PreOrder)
        .where(
            models.PreOrder.spreadsheet == spreadsheet,
            models.PreOrder.sheet_id == sheet,
            models.PreOrder.row_id == row_id,
        )
        .options(joinedload(models.PreOrder.info), joinedload(models.PreOrder.price))
    )
    return result.all()


async def get_order_id(session: AsyncSession, order_id: str) -> models.PreOrder | None:
    result = await session.scalars(
        sa.select(models.PreOrder)
        .where(models.PreOrder.order_id == order_id)
        .options(joinedload(models.PreOrder.info), joinedload(models.PreOrder.price))
        .limit(1)
    )
    return result.first()


async def update(
    session: AsyncSession, order: models.PreOrder, order_in: models.PreOrderUpdate, patch: bool = False
) -> models.PreOrder:
    update_data = order_in.model_dump(exclude={"price", "info"}, exclude_unset=patch)
    if order_in.has_response is None:
        update_data["has_response"] = order.has_response
    await session.execute(sa.update(models.PreOrder).where(models.PreOrder.id == order.id).values(**update_data))
    if order_in.info is not None:
        info_update = order_in.info.model_dump(exclude_unset=patch)
        await session.execute(
            sa.update(models.PreOrderInfo).where(models.PreOrderInfo.order_id == order.id).values(**info_update)
        )
    if order_in.price is not None:
        price_update = order_in.price.model_dump(exclude_unset=patch)
        await session.execute(
            sa.update(models.PreOrderPrice).where(models.PreOrderPrice.order_id == order.id).values(**price_update)
        )
    await session.commit()
    logger.info(f"PreOrder updated [id={order.id} order_id={order.order_id}]]")
    return await get(session, order.id)  # type: ignore


async def create(session: AsyncSession, pre_order_in: models.PreOrderCreate) -> models.PreOrder:
    pre_order = models.PreOrder(**pre_order_in.model_dump(exclude={"price", "info"}))
    pre_order.info = models.PreOrderInfo(order_id=pre_order.id, **pre_order_in.info.model_dump())
    pre_order.price = models.PreOrderPrice(order_id=pre_order.id, **pre_order_in.price.model_dump())
    session.add(pre_order)
    await session.commit()
    logger.info(f"PreOrder created [id={pre_order.id} order_id={pre_order.order_id}]]")
    return await get(session, pre_order.id)  # type: ignore


async def delete(session: AsyncSession, order_id: int):
    pre_order = await get(session, order_id)
    if pre_order:
        await session.execute(sa.delete(models.PreOrder).where(models.PreOrder.id == order_id))
        await session.commit()
        logger.info(f"PreOrder deleted [id={pre_order.id} order_id={pre_order.order_id}]]")
