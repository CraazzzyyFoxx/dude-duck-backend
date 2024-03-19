import re
import typing
from datetime import UTC, datetime

import sqlalchemy as sa
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from sqlalchemy.sql import func
from starlette import status

from src import models, schemas
from src.core import config, errors
from src.services.currency import flows as currency_flows
from src.services.integrations.sheets import flows as sheets_flows
from src.services.integrations.sheets import service as sheets_service
from src.services.order import flows as order_flows
from src.services.order import service as order_service
from src.services.tasks import service as tasks_service

BOOSTER_WITH_PRICE_REGEX = re.compile(config.app.username_regex + r" ?(\(\d+\))", flags=re.UNICODE & re.MULTILINE)
BOOSTER_REGEX = re.compile(config.app.username_regex, flags=re.UNICODE & re.MULTILINE)


async def get(session: AsyncSession, user_order_id: int) -> models.UserOrder | None:
    result = await session.scalars(
        sa.select(models.UserOrder)
        .where(models.UserOrder.id == user_order_id)
        .options(joinedload(models.UserOrder.user), joinedload(models.UserOrder.order))
    )
    return result.first()


async def get_by_order_id(session: AsyncSession, order_id: int) -> list[models.UserOrder]:
    result = await session.scalars(
        sa.select(models.UserOrder)
        .where(models.UserOrder.order_id == order_id)
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


async def sync_boosters_sheet(session: AsyncSession, order: models.Order) -> None:
    if config.app.sync_boosters:
        parser = await sheets_service.get_by_spreadsheet_sheet_read(session, order.spreadsheet, order.sheet_id)
        if parser is not None:
            user_orders = await get_by_order_id(session, order.id)
            query = sa.select(models.User).where(models.User.id.in_([d.user_id for d in user_orders]))
            users = await session.scalars(query)
            booster_str = await _boosters_to_str(session, order, user_orders, users.all())  # type: ignore
            tasks_service.update_order.delay(parser.model_dump(mode="json"), order.row_id, {"booster": booster_str})


async def create(
    session: AsyncSession,
    order: models.Order,
    user: models.User,
    boosters: list[models.UserOrder],
    price: float,
    sync: bool = True,
) -> models.UserOrder:
    user_order = models.UserOrder(
        order_id=order.id,
        user_id=user.id,
        dollars=price,
        order_date=order.date,
        completed=True if order.status == models.OrderStatus.Completed else False,
        paid=True if order.status_paid == models.OrderPaidStatus.Paid else False,
    )
    if user_order.paid:
        user_order.paid_at = datetime.now(UTC)
    if user_order.completed:
        user_order.completed_at = order.end_date if order.end_date else datetime.now(UTC)
    try:
        session.add(user_order)
        total_dollars = sum([d.dollars for d in boosters])
        if total_dollars + price > order.price.booster_dollar_fee:
            price_map: dict[int, float] = {b.id: b.dollars / total_dollars for b in boosters}
            for booster in boosters:
                booster.dollars = booster.dollars - price * price_map[booster.id]
            session.add_all(boosters)
        await session.commit()
        logger.info(f"Created UserOrder [order_id={user_order.order_id} user_id={user_order.user_id}]")
    except Exception as e:
        await session.rollback()
        raise e
    else:
        if not boosters:
            order_update = schemas.OrderUpdate(auth_date=datetime.now(UTC))
            new_order = await order_service.update(session, order, order_update)
            if sync:
                await sheets_flows.order_to_sheets(
                    session,
                    new_order,
                    await order_flows.format_order_system(session, new_order),
                )

        if sync:
            await sync_boosters_sheet(session, order)
    return user_order


async def delete_by_order_id(session: AsyncSession, order_id: int) -> None:
    user_orders = await get_by_order_id(session, order_id)
    for user_order in user_orders:
        logger.info(f"Deleted UserOrder [order_id={user_order.order_id} user_id={user_order.user_id}]")
        await session.delete(user_order)
    await session.commit()


async def update(
    session: AsyncSession,
    order: models.Order,
    user: models.User,
    update_model: schemas.UserOrderUpdate,
    sync: bool = True,
    patch: bool = False,
) -> models.UserOrder:
    boosters = await get_by_order_id(session, order.id)
    boosters_map: dict[int, models.UserOrder] = {b.user_id: b for b in boosters}
    if boosters_map.get(user.id) is None:
        raise errors.ApiHTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=[errors.ApiException(msg="The user is not a booster of this order", code="not_exist")],
        )

    try:
        if update_model.dollars is not None:
            total_price = sum([b.dollars for b in boosters])
            if update_model.dollars + total_price > order.price.booster_dollar_fee:
                raise errors.ApiHTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=[
                        errors.ApiException(
                            msg=f"The price for the booster is incorrect. "
                            f"Order price {order.price.booster_dollar_fee}, total price for boosters {total_price}."
                            f" \n{total_price} > {order.price.booster_dollar_fee}",
                            code="invalid_price",
                        )
                    ],
                )
        user_order = boosters_map[user.id]
        if update_model.completed is not None:
            if update_model.completed:
                user_order.completed_at = datetime.now(UTC)
            else:
                user_order.completed_at = None
        if update_model.paid is not None:
            if update_model.paid:
                user_order.paid_at = datetime.now(UTC)
            else:
                user_order.paid_at = None
        for key, value in update_model.model_dump(exclude_unset=True, exclude_defaults=patch).items():
            setattr(user_order, key, value)
        session.add(user_order)
        if sync:
            await sync_boosters_sheet(session, order)
        await session.commit()
        return user_order
    except Exception as e:
        await session.rollback()
        raise e


async def delete(
    session: AsyncSession,
    order: models.Order,
    user: models.User,
    sync: bool = True,
) -> models.UserOrder:
    boosters = await get_by_order_id(session, order.id)
    boosters_map: dict[int, models.UserOrder] = {b.user_id: b for b in boosters}
    to_delete = boosters_map.get(user.id)
    if to_delete is None:
        raise errors.ApiHTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=[errors.ApiException(msg="The user is not a booster of this order", code="not_exist")],
        )
    await session.execute(sa.delete(models.UserOrder).where(models.UserOrder.id == to_delete.id))
    await session.commit()
    if sync:
        await sync_boosters_sheet(session, order)
    logger.info(f"Deleted UserOrder [order_id={to_delete.order_id} user_id={to_delete.user_id}]")
    return to_delete


async def check_user_total_orders(session: AsyncSession, user: models.User) -> bool:
    result = await session.execute(
        sa.select(func.count(models.UserOrder.id)).where(
            models.UserOrder.user_id == user.id,
            models.UserOrder.completed == False,  # noqa: E712
        )
    )
    count = result.one()
    return bool(count[0] < user.max_orders)


async def update_booster_price(session: AsyncSession, old: models.Order, new: models.Order) -> None:
    boosters = await get_by_order_id(session, new.id)
    if not boosters:
        return
    old_price = await currency_flows.usd_to_currency(session, old.price.booster_dollar, old.date)
    new_price = await currency_flows.usd_to_currency(session, new.price.booster_dollar, new.date)
    delta = (new_price - old_price) / len(boosters)
    for booster in boosters:
        booster.dollars += delta
    session.add_all(boosters)
    await session.commit()


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
    order: models.Order,
    data: typing.Iterable[models.UserOrder],
    users: list[models.User],
) -> str | None:
    if len(users) == 1:
        return users[0].name
    resp = []
    users_map: dict[int, models.User] = {user.id: user for user in users}
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


async def boosters_to_str_sync(
    session: AsyncSession,
    order: models.Order,
    data: typing.Iterable[models.UserOrder],
    users_in: typing.Iterable[models.User],
) -> str | None:
    search = [d.user_id for d in data]
    users = [user_in for user_in in users_in if user_in.id in search]
    return await _boosters_to_str(session, order, data, users)
