import re
from datetime import datetime

from beanie import PydanticObjectId
from beanie.odm.operators.find.comparison import In

from app.core import config
from app.services.auth import flows as auth_flows
from app.services.auth import models as auth_models
from app.services.currency import flows as currency_flows
from app.services.orders import models as order_models
from app.services.settings import service as settings_service

from . import models

BOOSTER_WITH_PRICE_REGEX = re.compile(config.app.username_regex + r" ?(\(\d+\))", flags=re.UNICODE & re.MULTILINE)
BOOSTER_REGEX = re.compile(config.app.username_regex, flags=re.UNICODE & re.MULTILINE)


async def get(order_id: PydanticObjectId) -> models.UserOrder | None:
    return await models.UserOrder.find_one({"_id": order_id})


async def create(user_order_in: models.UserOrderCreate):
    user_order = models.UserOrder(order_id=user_order_in.order_id,
                                  user_id=user_order_in.user_id,
                                  dollars=user_order_in.dollars,
                                  completed=user_order_in.completed,
                                  paid=user_order_in.paid,
                                  method_payment=user_order_in.method_payment
                                  )
    if user_order_in.completed:
        user_order.completed_at = datetime.utcnow()
    if user_order_in.paid:
        user_order.paid_time = datetime.utcnow()
    return await user_order.create()


async def delete(user_order_id: PydanticObjectId):
    user_order = await get(user_order_id)
    await user_order.delete()


async def get_by_order_id(order_id: PydanticObjectId):
    return await models.UserOrder.find({"order_id": order_id}).to_list()


async def get_by_user_id(user_id: PydanticObjectId) -> list[models.UserOrder]:
    return await models.UserOrder.find({"user_id": user_id}).to_list()


async def get_by_order_id_user_id(order_id: PydanticObjectId, user_id: PydanticObjectId) -> models.UserOrder | None:
    return await models.UserOrder.find_one({"order_id": order_id, "user_id": user_id})


async def get_all() -> list[models.UserOrder]:
    return await models.UserOrder.find({}).to_list()


async def get_by_orders(orders_id: list[PydanticObjectId]) -> list[models.UserOrder]:
    return await models.UserOrder.find({"order_id": {"$in": orders_id}}).to_list()


async def update(user_order: models.UserOrder, user_order_in: models.UserOrderUpdate):
    user_order_data = user_order.model_dump()
    update_data = user_order_in.model_dump(exclude_none=True)

    for field in user_order_data:
        if field in update_data:
            if field == "paid":
                if update_data[field]:
                    setattr(user_order, "completed", True)
                    setattr(user_order, "completed_at", datetime.utcnow())
                    setattr(user_order, "paid_time", datetime.utcnow())
                else:
                    setattr(user_order, "paid_time", None)
            if field == "completed":
                if update_data[field]:
                    setattr(user_order, "completed", True)
                    setattr(user_order, "completed_at", datetime.utcnow())
                else:
                    setattr(user_order, "completed_at", None)
            setattr(user_order, field, update_data[field])

    await user_order.save_changes()
    return user_order


async def check_user_total_orders(user: auth_models.User) -> bool:
    count = await models.UserOrder.find({"user_id": user.id, "completed": False}).count()
    return bool(count < user.max_orders)


async def can_user_pick(user: auth_models.User) -> bool:
    if not user.is_verified:
        return False
    if not await check_user_total_orders(user):
        return False
    return True


async def update_booster_price(old: order_models.Order, new: order_models.Order):
    boosters = await get_by_order_id(new.id)
    if not boosters:
        return
    old_price = await usd_to_currency(old.price.price_booster_dollar, old.date)
    new_price = await usd_to_currency(new.price.price_booster_dollar, new.date)
    delta = (new_price - old_price) / len(boosters)
    for booster in boosters:
        booster.dollars += delta
        await booster.save_changes()


async def usd_to_currency(
        dollars: float,
        date: datetime,
        currency: str = "USD",
        *,
        with_round: bool = False,
        with_fee: bool = False
) -> float:
    settings = await settings_service.get()
    if currency == "USD":
        price = dollars
    else:
        currency_db = await currency_flows.get(date)
        price = dollars * currency_db.quotes[currency]
    if with_fee:
        price *= settings.accounting_fee
    if with_round:
        return round(price, settings.get_precision(currency))
    else:
        return price


async def currency_to_usd(
        wallet: float,
        date: datetime,
        currency: str = "USD",
        *,
        with_round: bool = False,
        with_fee: bool = False
) -> float:
    settings = await settings_service.get()
    if currency == "USD":
        price = wallet
    else:
        currency_db = await currency_flows.get(date)
        price = wallet / currency_db.quotes[currency]
    if with_fee:
        price *= settings.accounting_fee
    if with_round:
        return round(price, settings.get_precision(currency))
    else:
        return price


async def apply_round(wallet: float, currency: str = "USD"):
    settings = await settings_service.get()
    return round(wallet, settings.get_precision(currency))


def boosters_from_str(string: str) -> dict[str, int | None]:
    if string is None:
        return {}
    resp = {}
    boosters = BOOSTER_WITH_PRICE_REGEX.findall(string.lower())
    if len(boosters) > 0:
        for booster in boosters:
            resp[booster[0].strip().lower()] = int(booster[1].replace("(", "").replace(")", ""))
    else:
        booster = BOOSTER_REGEX.fullmatch(string.lower())
        if booster:
            resp[booster[0]] = None

    return resp


async def _boosters_to_str(order, data: list[models.UserOrder], users: list[auth_models.User]):
    if len(users) == 1:
        return users[0].name
    resp = []
    for d in data:
        for booster in users:
            if booster.id == d.user.id:
                price = await usd_to_currency(d.dollars, order.date, currency='RUB', with_round=True)
                resp.append(f"{booster.name}({price})")
    return ' + '.join(resp)


async def boosters_to_str(order, data: list[models.UserOrder]) -> str:
    users = await auth_flows.models.User.find(In(auth_flows.models.User.id, [d.user.id for d in data])).to_list()
    return await _boosters_to_str(order, data, users)


async def boosters_to_str_sync(order, data: list[models.UserOrder], users_in: list[auth_models.User]) -> str:
    users = []
    search = [d.user_id for d in data]
    for user_in in users_in:
        if user_in.id in search:
            users.append(user_in)
    return await _boosters_to_str(order, data, users)


async def _boosters_from_order(order: order_models.Order, users_in: list[auth_models.User]):
    completed = True if order.status == order_models.OrderStatus.Completed else False
    paid = True if order.status_paid == order_models.OrderPaidStatus.Paid else False
    boosters = boosters_from_str(order.booster)
    for booster, price in boosters.items():
        for user in users_in:
            if user.name == booster:
                x = await get_by_order_id_user_id(order.id, user.id)
                if x is None:
                    if price is None:
                        dollars = await usd_to_currency(order.price.price_booster_dollar, order.date, with_fee=True)
                        dollars /= len(boosters)
                    else:
                        dollars = await currency_to_usd(price, order.date, currency="RUB")
                    b = models.UserOrderCreate(
                        order_id=order.id, user_id=user.id, dollars=dollars, completed=completed, paid=paid
                    )
                    await create(b)
                    break


async def boosters_from_order(order) -> None:
    users = await auth_flows.service.get_all()
    return await _boosters_from_order(order, users)


async def boosters_from_order_sync(order, users: list[auth_models.User]) -> None:
    return await _boosters_from_order(order, users)
