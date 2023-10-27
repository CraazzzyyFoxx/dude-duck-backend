import re
import typing
from datetime import datetime

import sqlalchemy as sa
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from sqlalchemy.sql import func
from src.core import config
from src.services.auth import models as auth_models
from src.services.auth import service as auth_service
from src.services.currency import flows as currency_flows
from src.services.orders import models as order_models

from . import models

BOOSTER_WITH_PRICE_REGEX = re.compile(config.app.username_regex + r" ?(\(\d+\))", flags=re.UNICODE & re.MULTILINE)
BOOSTER_REGEX = re.compile(config.app.username_regex, flags=re.UNICODE & re.MULTILINE)


async def get(session: AsyncSession, user_order_id: int) -> models.UserOrder | None:
    result = await session.scalars(
        sa.select(models.UserOrder)
        .where(models.UserOrder.id == user_order_id)
        .options(joinedload(models.UserOrder.user), joinedload(models.UserOrder.order))
    )
    return result.first()


async def create(
    session: AsyncSession, order: order_models.Order, user_order_in: models.UserOrderCreate
) -> models.UserOrder:
    user_order = models.UserOrder(**user_order_in.model_dump())
    if user_order_in.completed:
        user_order.completed_at = order.end_date if order.end_date is not None else datetime.utcnow()
    if user_order_in.paid:
        user_order.paid_at = datetime.utcnow()
    session.add(user_order)
    await session.commit()
    logger.info(f"Created UserOrder [order_id={user_order.order_id} user_id={user_order.user_id}]")
    return user_order


async def delete(session: AsyncSession, user_order_id: int) -> None:
    user_order = await get(session, user_order_id)
    if user_order:
        await session.delete(user_order)
        await session.commit()
        logger.info(f"Deleted UserOrder [order_id={user_order.order_id} user_id={user_order.user_id}]")


async def delete_by_order_id(session: AsyncSession, order_id: int) -> None:
    user_orders = await get_by_order_id(session, order_id)
    for user_order in user_orders:
        logger.info(f"Deleted UserOrder [order_id={user_order.order_id} user_id={user_order.user_id}]")
        await session.delete(user_order)
    await session.commit()


async def get_by_order_id(session: AsyncSession, order_id: int) -> list[models.UserOrder]:
    result = await session.scalars(
        sa.select(models.UserOrder)
        .where(models.UserOrder.order_id == order_id)
        .options(joinedload(models.UserOrder.user), joinedload(models.UserOrder.order))
    )
    return result.all()  # type: ignore


async def get_by_user_id(session: AsyncSession, user_id: int) -> list[models.UserOrder]:
    result = await session.scalars(
        sa.select(models.UserOrder)
        .where(models.UserOrder.user_id == user_id)
        .options(joinedload(models.UserOrder.user), joinedload(models.UserOrder.order))
    )
    return result.all()  # type: ignore


async def get_by_order_id_user_id(session: AsyncSession, order_id: int, user_id: int) -> models.UserOrder | None:
    result = await session.scalars(
        sa.select(models.UserOrder)
        .where(models.UserOrder.order_id == order_id)
        .where(models.UserOrder.user_id == user_id)
        .options(joinedload(models.UserOrder.user), joinedload(models.UserOrder.order))
    )
    return result.first()


async def get_by_orders(session: AsyncSession, orders_id: typing.Iterable[int]) -> typing.Sequence[models.UserOrder]:
    result = await session.scalars(
        sa.select(models.UserOrder)
        .where(models.UserOrder.order_id.in_(orders_id))
        .options(joinedload(models.UserOrder.user), joinedload(models.UserOrder.order))
    )
    return result.all()


async def update(
    session: AsyncSession, user_order: models.UserOrder, user_order_in: models.UserOrderUpdate
) -> models.UserOrder:
    update_data = user_order_in.model_dump(exclude_defaults=True)
    await session.execute(sa.update(models.UserOrder).where(models.UserOrder.id == user_order.id).values(**update_data))
    await session.commit()
    logger.info(f"Updated UserOrder [order_id={user_order.order_id} user_id={user_order.user_id}]")
    return await get(session, user_order.id)


async def patch(
    session: AsyncSession, user_order: models.UserOrder, user_order_in: models.UserOrderUpdate
) -> models.UserOrder:
    update_data = user_order_in.model_dump(exclude_defaults=True, exclude_unset=True)
    await session.execute(sa.update(models.UserOrder).where(models.UserOrder.id == user_order.id).values(**update_data))
    await session.commit()
    logger.info(f"Patched UserOrder [order_id={user_order.order_id} user_id={user_order.user_id}]")
    return await get(session, user_order.id)


async def bulk_update_price(session: AsyncSession, order_id: int, price: float, inc=False) -> None:
    await session.execute(
        sa.update(models.UserOrder)
        .where(models.UserOrder.order_id == order_id)
        .values(dollars=models.UserOrder.dollars + price if inc else price)
    )
    await session.commit()


async def check_user_total_orders(session: AsyncSession, user: auth_models.User) -> bool:
    result = await session.execute(
        sa.select(
            func.count(models.UserOrder.id))
        .where(models.UserOrder.user_id == user.id, models.UserOrder.completed == False)
    )
    count = result.first()
    return bool(count[0] < user.max_orders)


async def update_booster_price(session: AsyncSession, old: order_models.Order, new: order_models.Order) -> None:
    boosters = await get_by_order_id(session, new.id)
    if not boosters:
        return
    old_price = await currency_flows.usd_to_currency(session, old.price.price_booster_dollar, old.date)
    new_price = await currency_flows.usd_to_currency(session, new.price.price_booster_dollar, new.date)
    delta = (new_price - old_price) / len(boosters)
    await bulk_update_price(session, new.id, delta, inc=True)


def boosters_from_str(string: str) -> dict[str, int | None]:
    if string is None:
        return {}
    string = string.lower()
    resp: dict[str, int | None] = {}
    boosters = BOOSTER_WITH_PRICE_REGEX.findall(string)
    if len(boosters) > 0:
        for booster in boosters:
            resp[booster[0].strip()] = int(booster[1].replace("(", "").replace(")", ""))
    else:
        booster = BOOSTER_REGEX.fullmatch(string)
        if booster:
            resp[booster[0]] = None
    return resp


async def _boosters_to_str(
    session: AsyncSession,
    order: order_models.Order,
    data: typing.Iterable[models.UserOrder],
    users: list[auth_models.User],
) -> str | None:
    if len(users) == 1:
        return users[0].name
    resp = []
    users_map: dict[int, auth_models.User] = {user.id: user for user in users}
    for d in data:
        booster = users_map.get(d.user_id, None)
        if booster:
            price = await currency_flows.usd_to_currency(
                session, d.dollars, order.date, currency="RUB", with_round=True
            )
            resp.append(f"{booster.name}({int(price)})")
    if resp:
        return " + ".join(resp)
    return None


async def boosters_to_str(session: AsyncSession, order, data: list[models.UserOrder]) -> str:
    users = await auth_service.get_by_ids(session, [d.user_id for d in data])
    return await _boosters_to_str(session, order, data, users)


async def boosters_to_str_sync(
    session: AsyncSession,
    order: order_models.Order,
    data: typing.Iterable[models.UserOrder],
    users_in: typing.Iterable[auth_models.User]
) -> str | None:
    search = [d.user_id for d in data]
    users = [user_in for user_in in users_in if user_in.id in search]
    return await _boosters_to_str(session, order, data, users)