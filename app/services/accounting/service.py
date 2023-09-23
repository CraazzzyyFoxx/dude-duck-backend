import re
from datetime import datetime

from beanie import PydanticObjectId
from beanie.odm.operators.find.comparison import In

from app.core import config
from app.services.auth import flows as auth_flows
from app.services.auth import models as auth_models
from app.services.currency import flows as currency_flows
from app.services.orders import models as order_models

from . import models

BOOSTER_WITH_PRICE_REGEX = re.compile(config.app.username_regex + r" ?(\(\d+\))", flags=re.UNICODE & re.MULTILINE)
BOOSTER_REGEX = re.compile(config.app.username_regex, flags=re.UNICODE & re.MULTILINE)


async def get(order_id: PydanticObjectId) -> models.UserOrder | None:
    return await models.UserOrder.find_one({"_id": order_id})


async def create(user_order_in: models.UserOrderCreate) -> models.UserOrder:
    user_order = models.UserOrder(
        order_id=user_order_in.order_id,
        user_id=user_order_in.user_id,
        dollars=user_order_in.dollars,
        completed=user_order_in.completed,
        paid=user_order_in.paid,
        method_payment=user_order_in.method_payment,
        order_date=user_order_in.order_date,
    )
    if user_order_in.completed:
        user_order.completed_at = datetime.utcnow()
    if user_order_in.paid:
        user_order.paid_time = datetime.utcnow()
    return await user_order.create()


async def delete(user_order_id: PydanticObjectId) -> None:
    user_order = await get(user_order_id)
    await user_order.delete()


async def get_by_order_id(order_id: PydanticObjectId) -> list[models.UserOrder]:
    return await models.UserOrder.find({"order_id": order_id}).to_list()


async def get_by_user_id(user_id: PydanticObjectId) -> list[models.UserOrder]:
    return await models.UserOrder.find({"user_id": user_id}).to_list()


async def get_by_order_id_user_id(order_id: PydanticObjectId, user_id: PydanticObjectId) -> models.UserOrder | None:
    return await models.UserOrder.find_one({"order_id": order_id, "user_id": user_id})


async def get_all() -> list[models.UserOrder]:
    return await models.UserOrder.find({}).to_list()


async def get_by_orders(orders_id: list[PydanticObjectId]) -> list[models.UserOrder]:
    return await models.UserOrder.find({"order_id": {"$in": orders_id}}).to_list()


async def update(user_order: models.UserOrder, user_order_in: models.UserOrderUpdate) -> models.UserOrder:
    user_order_data = user_order.model_dump()
    update_data = user_order_in.model_dump(exclude_none=True)

    for field in user_order_data:
        if field in update_data:
            if field == "paid":
                if update_data[field]:
                    user_order.completed = True
                    user_order.completed_at = datetime.utcnow()
                    user_order.paid_time = datetime.utcnow()
                else:
                    user_order.paid_time = None
            if field == "completed":
                if update_data[field]:
                    user_order.completed = True
                    user_order.completed_at = datetime.utcnow()
                else:
                    user_order.completed_at = None
            setattr(user_order, field, update_data[field])

    await user_order.save_changes()
    return user_order


async def bulk_update_price(order_id: PydanticObjectId, price: float) -> None:
    await models.UserOrder.find({"order_id": order_id}).update({"$set": {"dollars": price}})


async def bulk_decrement_price(order_id: PydanticObjectId, price: float, is_dec=True) -> None:
    if is_dec:
        price = -price
    await models.UserOrder.find({"order_id": order_id}).update({"$inc": {"dollars": price}})


async def check_user_total_orders(user: auth_models.User) -> bool:
    count = await models.UserOrder.find({"user_id": user.id, "completed": False}).count()
    return bool(count < user.max_orders)


async def update_booster_price(old: order_models.Order, new: order_models.Order) -> None:
    boosters = await get_by_order_id(new.id)
    if not boosters:
        return
    old_price = await currency_flows.usd_to_currency(old.price.price_booster_dollar, old.date)
    new_price = await currency_flows.usd_to_currency(new.price.price_booster_dollar, new.date)
    delta = (new_price - old_price) / len(boosters)
    for booster in boosters:
        booster.dollars += delta
        await booster.save_changes()


def boosters_from_str(string: str) -> dict[str, int | None]:
    if string is None:
        return {}
    resp: dict[str, int | None] = {}
    boosters = BOOSTER_WITH_PRICE_REGEX.findall(string.lower())
    if len(boosters) > 0:
        for booster in boosters:
            resp[booster[0].strip().lower()] = int(booster[1].replace("(", "").replace(")", ""))
    else:
        booster = BOOSTER_REGEX.fullmatch(string.lower())
        if booster:
            resp[booster[0]] = None

    return resp


async def _boosters_to_str(order, data: list[models.UserOrder], users: list[auth_models.User]) -> str | None:
    if len(users) == 1:
        return users[0].name
    resp = []
    users_map: dict[PydanticObjectId, auth_models.User] = {user.id: user for user in users}
    for d in data:
        booster = users_map.get(d.user_id, None)
        if booster:
            price = await currency_flows.usd_to_currency(d.dollars, order.date, currency="RUB", with_round=True)
            resp.append(f"{booster.name}({int(price)})")
    if resp:
        return " + ".join(resp)
    return None


async def boosters_to_str(order, data: list[models.UserOrder]) -> str:
    users = await auth_flows.models.User.find(In(auth_flows.models.User.id, [d.user_id for d in data])).to_list()
    return await _boosters_to_str(order, data, users)


async def boosters_to_str_sync(order, data: list[models.UserOrder], users_in: list[auth_models.User]) -> str | None:
    search = [d.user_id for d in data]
    users = [user_in for user_in in users_in if user_in.id in search]
    return await _boosters_to_str(order, data, users)
