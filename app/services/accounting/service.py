import re
import typing
from datetime import datetime

from loguru import logger
from tortoise.expressions import F

from app.core import config
from app.services.auth import models as auth_models
from app.services.auth import service as auth_service
from app.services.currency import flows as currency_flows
from app.services.orders import models as order_models

from . import models

BOOSTER_WITH_PRICE_REGEX = re.compile(config.app.username_regex + r" ?(\(\d+\))", flags=re.UNICODE & re.MULTILINE)
BOOSTER_REGEX = re.compile(config.app.username_regex, flags=re.UNICODE & re.MULTILINE)


async def get(user_order_id: int) -> models.UserOrder | None:
    return await models.UserOrder.filter(id=user_order_id).prefetch_related("order", "user").first()


async def create(order: order_models.Order, user_order_in: models.UserOrderCreate) -> models.UserOrder:
    user_order = models.UserOrder(**user_order_in.model_dump())
    if user_order_in.completed:
        user_order.completed_at = order.end_date if order.end_date is not None else datetime.utcnow()
    if user_order_in.paid:
        user_order.paid_at = datetime.utcnow()
    await user_order.save()
    logger.info(f"Created UserOrder [order_id={user_order.order_id} user_id={user_order.user_id}]")
    return user_order


async def delete(user_order_id: int) -> None:
    user_order = await get(user_order_id)
    if user_order:
        logger.info(f"Deleted UserOrder [order_id={user_order.order_id} user_id={user_order.user_id}]")
        await user_order.delete()


async def delete_by_order_id(order_id: int) -> None:
    user_orders = await get_by_order_id(order_id)
    for user_order in user_orders:
        logger.info(f"Deleted UserOrder [order_id={user_order.order_id} user_id={user_order.user_id}]")
        await user_order.delete()


async def get_by_order_id(order_id: int) -> list[models.UserOrder]:
    return await models.UserOrder.filter(order_id=order_id).prefetch_related("order", "user")


async def get_by_user_id(user_id: int) -> list[models.UserOrder]:
    return await models.UserOrder.filter(user_id=user_id).prefetch_related("order", "user")


async def get_by_order_id_user_id(order_id: int, user_id: int) -> models.UserOrder | None:
    return await models.UserOrder.filter(order_id=order_id, user_id=user_id).prefetch_related("order", "user").first()


async def get_by_orders(orders_id: typing.Iterable[int]) -> list[models.UserOrder]:
    return await models.UserOrder.filter(order_id__in=orders_id).prefetch_related("order", "user")


async def update(user_order: models.UserOrder, user_order_in: models.UserOrderUpdate) -> models.UserOrder:
    update_data = user_order_in.model_dump(exclude_defaults=True)
    user_order = await user_order.update_from_dict(update_data)
    await user_order.save()
    logger.info(f"Updated UserOrder [order_id={user_order.order_id} user_id={user_order.user_id}]")
    return user_order


async def patch(user_order: models.UserOrder, user_order_in: models.UserOrderUpdate) -> models.UserOrder:
    update_data = user_order_in.model_dump(exclude_defaults=True, exclude_unset=True)
    user_order = await user_order.update_from_dict(update_data)
    await user_order.save(update_fields=update_data.keys())
    logger.info(f"Patched UserOrder [order_id={user_order.order_id} user_id={user_order.user_id}]")
    return user_order


async def bulk_update_price(order_id: int, price: float, inc=False) -> None:
    func = F("dollars") + price if inc else price
    await models.UserOrder.filter(order_id=order_id).update(dollars=func)


async def check_user_total_orders(user: auth_models.User) -> bool:
    count = await models.UserOrder.filter(user_id=user.id, completed=False).count()
    return bool(count < user.max_orders)


async def update_booster_price(old: order_models.Order, new: order_models.Order) -> None:
    boosters = await get_by_order_id(new.id)
    if not boosters:
        return
    old_price = await currency_flows.usd_to_currency(old.price.price_booster_dollar, old.date)
    new_price = await currency_flows.usd_to_currency(new.price.price_booster_dollar, new.date)
    delta = (new_price - old_price) / len(boosters)
    await bulk_update_price(new.id, delta, inc=True)


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
    order: order_models.Order, data: typing.Iterable[models.UserOrder], users: list[auth_models.User]
) -> str | None:
    if len(users) == 1:
        return users[0].name
    resp = []
    users_map: dict[int, auth_models.User] = {user.id: user for user in users}
    for d in data:
        booster = users_map.get(d.user_id, None)
        if booster:
            price = await currency_flows.usd_to_currency(d.dollars, order.date, currency="RUB", with_round=True)
            resp.append(f"{booster.name}({int(price)})")
    if resp:
        return " + ".join(resp)
    return None


async def boosters_to_str(order, data: list[models.UserOrder]) -> str:
    users = await auth_service.get_by_ids([d.user_id for d in data])
    return await _boosters_to_str(order, data, users)


async def boosters_to_str_sync(
    order: order_models.Order, data: typing.Iterable[models.UserOrder], users_in: typing.Iterable[auth_models.User]
) -> str | None:
    search = [d.user_id for d in data]
    users = [user_in for user_in in users_in if user_in.id in search]
    return await _boosters_to_str(order, data, users)
