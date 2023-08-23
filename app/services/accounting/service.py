import re
from datetime import datetime

from beanie import PydanticObjectId
from beanie.odm.operators.find.comparison import In

from app.core import config
from app.services.auth import flows as auth_flows

from . import models

BOOSTER_WITH_PRICE_REGEX = re.compile(config.app.username_regex + r"(\(\d+\))", flags=re.UNICODE & re.MULTILINE)
BOOSTER_REGEX = re.compile(config.app.username_regex, flags=re.UNICODE & re.MULTILINE)


async def get(order_id: PydanticObjectId) -> models.UserOrder | None:
    return await models.UserOrder.find_one({"_id": order_id})


async def create(user_order_in: models.UserOrderCreate):
    user_order = models.UserOrder(order=user_order_in.order_id,
                                  user=user_order_in.user_id,
                                  dollars=user_order_in.dollars,
                                  completed=user_order_in.completed,
                                  paid=user_order_in.paid,
                                  method_payment=user_order_in.method_payment
                                  )
    if user_order_in.paid:
        user_order.paid_time = datetime.utcnow()
    return await user_order.create()


async def delete(user_order_id: PydanticObjectId):
    user_order = await get(user_order_id)
    await user_order.delete()


async def get_by_order_id(order_id: PydanticObjectId):
    return await models.UserOrder.find(models.UserOrder.order.id == order_id, fetch_links=True).to_list()


async def get_by_order_id_without_prefetch(order_id: PydanticObjectId):
    return await models.UserOrder.find(models.UserOrder.order.id == order_id).to_list()


async def get_by_user_id(user_id: PydanticObjectId) -> list[models.UserOrder]:
    return await models.UserOrder.find(models.UserOrder.user.id == user_id, fetch_links=True).to_list()


async def get_by_order_id_user_id(order_id: PydanticObjectId, user_id: PydanticObjectId) -> models.UserOrder | None:
    return await models.UserOrder.find_one(models.UserOrder.user.id == user_id,
                                           models.UserOrder.order.id == order_id,
                                           fetch_links=True)


async def get_all() -> list[models.UserOrder]:
    return await models.UserOrder.find({}).to_list()


async def get_by_sheet_prefetched(spreadsheet: str, sheet: int) -> list[models.UserOrder]:
    return await models.UserOrder.find({"order.spreadsheet": spreadsheet, "order.sheet_id": sheet},
                                       fetch_links=True).to_list()


async def get_by_user_and_status(
        user_id: PydanticObjectId,
        status: models.OrderStatus
) -> list[models.Order]:
    data = await models.UserOrder.find({"user.id": user_id}).to_list()
    return await models.Order.find({"_id": {"$in": [d.order.id for d in data]}, "status": status}).to_list()


async def update(user_order: models.UserOrder, user_order_in: models.UserOrderUpdate):
    user_order_data = user_order.model_dump()
    update_data = user_order_in.model_dump(exclude_none=True)

    for field in user_order_data:
        if field in update_data:
            if field == "paid":
                setattr(user_order, "completed", True)
                setattr(user_order, "paid_time", datetime.utcnow())
            setattr(user_order, field, update_data[field])

    await user_order.save_changes()
    return user_order


async def check_user_total_orders(user: auth_flows.models.User) -> bool:
    count = await models.UserOrder.find({"user._id": user.id, "completed": False}, fetch_links=True).count()
    return bool(count < user.max_orders)


async def can_user_pick(user: auth_flows.models.User) -> bool:
    if not user.is_verified:
        return False
    if not await check_user_total_orders(user):
        return False
    return True


async def update_booster_price(old, new):
    boosters = await get_by_order_id(new.id)
    if not boosters:
        return
    delta = (new.price.price_booster_dollar_fee - old.price.price_booster_dollar_fee) / len(boosters)
    for booster in boosters:
        booster.dollars += delta
        await booster.save_changes()


def calculate_price_dollars(price: float):
    return round(price, config.app.accounting_precision_dollar)


def calculate_price_rub(price: float, exchange: float):
    return int(round(price * exchange, config.app.accounting_precision_rub))


def calculate_price_gold(price: float, exchange: float):
    return round(price * exchange, config.app.accounting_precision_gold)


def boosters_from_str(string: str) -> dict[str, int | None]:
    resp = {}
    boosters = BOOSTER_REGEX.findall(string.lower())
    for booster in boosters:
        data = BOOSTER_WITH_PRICE_REGEX.fullmatch("".join([d.strip() for d in booster]))
        if data:
            groups = data.groups()
            resp[groups[0].strip().lower()] = int(groups[1].replace("(", "").replace(")", ""))
        else:
            resp[booster.strip().lower()] = None

    return resp


def _boosters_to_str(order, data: list[models.UserOrder], users: list[auth_flows.models.User]):
    if len(users) == 1:
        return users[0].name
    resp = []
    for d in data:
        for booster in users:
            if booster.id == d.user.id:
                resp.append(f"{booster.name}({calculate_price_rub(d.dollars, order.exchange)})")
    return ' + '.join(resp)


async def boosters_to_str(order, data: list[models.UserOrder]) -> str:
    users = await auth_flows.models.User.find(In(auth_flows.models.User.id, [d.user.id for d in data])).to_list()
    return _boosters_to_str(order, data, users)


def boosters_to_str_sync(order, data: list[models.UserOrder], users_in: list[auth_flows.models.User]) -> str:
    users = []
    search = [d.user.id for d in data]
    for user_in in users_in:
        if user_in.id in search:
            users.append(user_in)
    return _boosters_to_str(order, data, users)


async def boosters_from_order(order) -> None:
    if order.booster is None:
        return
    completed = True if order.status == "Completed" else False
    paid = True if order.status_paid == "Paid" else False
    boosters = boosters_from_str(order.booster)
    for booster, price in boosters.items():
        if user := await auth_flows.get_booster_by_name(booster):
            dollars = order.price.price_booster_dollar_fee / len(boosters) if not price else price / order.exchange
            b = models.UserOrderCreate(order_id=order.id, user_id=user.id,
                                       dollars=dollars, completed=completed, paid=paid)
            await create(b)


async def boosters_from_order_sync(order, users_in: list[auth_flows.models.User]) -> None:
    if order.booster is None:
        return
    completed = True if order.status == "Completed" else False
    paid = True if order.status_paid == "Paid" else False
    boosters = boosters_from_str(order.booster)
    for booster, price in boosters.items():
        for user in users_in:
            if user.name == booster:
                dollars = order.price.price_booster_dollar_fee / len(boosters) if not price else price / order.exchange
                b = models.UserOrderCreate(order_id=order.id, user_id=user.id,
                                           dollars=dollars, completed=completed, paid=paid)
                await create(b)
