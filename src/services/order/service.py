import copy
import typing

import sqlalchemy as sa
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from src.services.accounting import service as accounting_service
from src.services.sheets import service as sheets_service
from src.services.tasks import service as tasks_service

from . import models


async def get(session: AsyncSession, order_id: int) -> models.Order | None:
    result = await session.scalars(
        sa.select(models.Order)
        .where(models.Order.id == order_id)
        .options(joinedload(models.Order.info), joinedload(models.Order.price), joinedload(models.Order.credentials))
        .limit(1)
    )
    return result.first()


async def get_all(session: AsyncSession) -> typing.Sequence[models.Order]:
    result = await session.scalars(
        sa.select(models.Order).options(
            joinedload(models.Order.info), joinedload(models.Order.price), joinedload(models.Order.credentials)
        )
    )
    return result.all()


async def get_all_by_sheet(session: AsyncSession, spreadsheet: str, sheet: int) -> typing.Sequence[models.Order]:
    result = await session.scalars(
        sa.select(models.Order)
        .where(models.Order.spreadsheet == spreadsheet, models.Order.sheet_id == sheet)
        .options(joinedload(models.Order.info), joinedload(models.Order.price), joinedload(models.Order.credentials))
    )
    return result.all()


async def get_order_id(session: AsyncSession, order_id: str) -> models.Order | None:
    result = await session.scalars(
        sa.select(models.Order)
        .where(models.Order.order_id == order_id)
        .options(joinedload(models.Order.info), joinedload(models.Order.price), joinedload(models.Order.credentials))
        .limit(1)
    )
    return result.first()


async def get_by_ids(session: AsyncSession, ids: list[int]) -> typing.Sequence[models.Order]:
    result = await session.scalars(
        sa.select(models.Order)
        .where(models.Order.id.in_(ids))
        .options(joinedload(models.Order.info), joinedload(models.Order.price), joinedload(models.Order.credentials))
    )
    return result.all()


async def update_with_sync(session: AsyncSession, order: models.Order, order_in: models.OrderUpdate) -> models.Order:
    order = await patch(session, order, order_in)
    parser = await sheets_service.get_by_spreadsheet_sheet_read(session, order.spreadsheet, order.sheet_id)
    if parser is not None:
        tasks_service.update_order.delay(parser.model_dump(mode="json"), order.row_id, order_in.model_dump())
    return order


async def patch(session: AsyncSession, order: models.Order, order_in: models.OrderUpdate) -> models.Order:
    old = copy.deepcopy(order)
    update_data = order_in.model_dump(
        exclude_defaults=True, exclude_unset=True, exclude={"price", "info", "credentials"}
    )
    await session.execute(sa.update(models.Order).where(models.Order.id == order.id).values(update_data))

    if order_in.info is not None:
        info_update = order_in.info.model_dump(exclude_defaults=True, exclude_unset=True)
        await session.execute(sa.update(models.OrderInfo).filter_by(order_id=order.id).values(info_update))
    if order_in.credentials is not None:
        credentials_update = order_in.credentials.model_dump(exclude_defaults=True, exclude_unset=True)
        await session.execute(
            sa.update(models.OrderCredentials).filter_by(order_id=order.id).values(credentials_update)
        )
    if order_in.price is not None:
        price_update = order_in.price.model_dump(exclude_defaults=True, exclude_unset=True)
        await session.execute(sa.update(models.OrderPrice).filter_by(order_id=order.id).values(price_update))
        await accounting_service.update_booster_price(session, old, order)
    if order.status == models.OrderStatus.Refund:
        user_orders = await accounting_service.get_by_order_id(session, order.id)
        for user_order in user_orders:
            user_order.completed = False
            user_order.paid = False
            user_order.refunded = True
        session.add_all(user_orders)
    await session.commit()
    logger.info(f"Order patched [id={order.id} order_id={order.order_id}]]")
    return await get(session, order.id)  # type: ignore


async def update(session: AsyncSession, order: models.Order, order_in: models.OrderUpdate) -> models.Order:
    old = copy.deepcopy(order)
    update_data = order_in.model_dump(exclude={"price", "info", "credentials"})
    await session.execute(sa.update(models.Order).where(models.Order.id == order.id).values(update_data))
    if order_in.info is not None:
        info_update = order_in.info.model_dump(exclude_defaults=True)
        if info_update:
            await session.execute(sa.update(models.OrderInfo).filter_by(order_id=order.id).values(info_update))
    if order_in.credentials is not None:
        credentials_update = order_in.credentials.model_dump(exclude_defaults=True)
        if credentials_update:
            await session.execute(
                sa.update(models.OrderCredentials).filter_by(order_id=order.id).values(credentials_update)
            )
    if order_in.price is not None:
        update_data_price = order_in.price.model_dump(exclude_defaults=True)
        if update_data_price:
            await session.execute(sa.update(models.OrderPrice).filter_by(order_id=order.id).values(update_data_price))
            await accounting_service.update_booster_price(session, old, order)

    if order.status == models.OrderStatus.Refund:
        user_orders = await accounting_service.get_by_order_id(session, order.id)
        for user_order in user_orders:
            user_order.completed = False
            user_order.paid = False
            user_order.refunded = True
        session.add_all(user_orders)
    await session.commit()
    logger.info(f"Order updated [id={order.id} order_id={order.order_id}]]")
    return await get(session, order.id)  # type: ignore


async def delete(session: AsyncSession, order_id: int) -> None:
    order = await get(session, order_id)
    if order:
        await session.execute(sa.delete(models.Order).where(models.Order.id == order_id))
        await session.commit()
        logger.info(f"Order deleted [id={order.id} order_id={order.order_id}]]")


async def create(session: AsyncSession, order_in: models.OrderCreate) -> models.Order:
    order = models.Order(**order_in.model_dump(exclude={"price", "info", "credentials"}))
    order.info = models.OrderInfo(order_id=order.id, **order_in.info.model_dump())
    order.price = models.OrderPrice(order_id=order.id, **order_in.price.model_dump())
    order.credentials = models.OrderCredentials(order_id=order.id, **order_in.credentials.model_dump())
    session.add(order)
    await session.commit()
    logger.info(f"Order created [id={order.id} order_id={order.order_id}]]")
    return await get(session, order.id)  # type: ignore
