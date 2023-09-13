from datetime import datetime

from beanie import PydanticObjectId
from fastapi import HTTPException
from starlette import status

from app.services.auth import flows as auth_flows
from app.services.auth import models as auth_models
from app.services.auth import service as auth_service
from app.services.auth.models import User
from app.services.orders import models as order_models
from app.services.orders import service as order_service
from app.services.permissions import service as permissions_service
from app.services.sheets import service as sheets_service
from app.services.tasks import service as tasks_service
from app.services.telegram.message import service as messages_service

from . import models, service


async def check_user_total_orders(user: auth_models.User) -> bool:
    if await service.check_user_total_orders(user):
        return True
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                        detail=[{"msg": "You have reached the limit of active orders."}])


async def can_user_pick(user: auth_models.User) -> bool:
    if not user.is_verified:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail=[{"msg": "Only verified users can fulfill orders"}])
    await check_user_total_orders(user)
    return True


async def can_user_pick_order(user: auth_models.User, order: order_service.models.Order):
    await can_user_pick(user)
    order_user = await service.get_by_order_id_user_id(order.id, user.id)
    if order_user:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail=[{"msg": "You are already assigned to this order"}])
    return True


async def check_total_dollars(
        order: order_service.models.Order,
        boosters: list[models.UserOrder],
        price: float
) -> bool:
    p = await service.usd_to_currency(order.price.price_booster_dollar, order.date, with_fee=True)
    total = sum([b.dollars for b in boosters]) + price
    if p < total:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail=[{"msg": f"The price for the booster is incorrect. "
                                            f"Order price {p}, total price for boosters {total}. \n"
                                            f"{total}>{p}"}])
    return True


async def add_booster(
        order: order_service.models.Order,
        user: auth_models.User,
        price: float = None
) -> models.UserOrder:
    await can_user_pick(user)
    boosters = await service.get_by_order_id(order.id)
    if price is None:
        percent = 1 / (len(boosters) + 1)
        price = await service.usd_to_currency(order.price.price_booster_dollar, order.date, with_fee=True)
        price = price * percent
        for booster in boosters:
            await service.update(booster, models.UserOrderUpdate(dollars=price))
    else:
        await check_total_dollars(order, boosters, price)
        p = await service.usd_to_currency(order.price.price_booster_dollar, order.date, with_fee=True)
        minus_dollars = (p - price) / len(boosters)
        for booster in boosters:
            await service.update(booster, models.UserOrderUpdate(dollars=booster.dollars - minus_dollars))

    data = await service.create(models.UserOrderCreate(order_id=order.id, user_id=user.id, dollars=price))

    booster_str = await service.boosters_to_str(order, await service.get_by_order_id(order.id))
    if not boosters:
        await order_service.update_with_sync(
            order, order_models.OrderUpdate(booster=booster_str,  auth_date=datetime.utcnow())
        )
    else:
        await order_service.update_with_sync(order, order_models.OrderUpdate(booster=booster_str))
    return data


async def update_boosters_percent(
        order: order_service.models.Order,
        data: models.SheetUserOrderCreate
) -> list[models.UserOrder]:
    users: list[tuple[PydanticObjectId, float]] = []
    users_id = []
    for item in data.items:
        user = await auth_flows.get_booster_by_name(item.username)
        users.append((user.id, item.percent))
        users_id.append(user.id)

    boosters = await service.get_by_order_id(order.id)
    boosters_map = {booster.user_id.id: booster for booster in boosters}
    if [u[0] for u in users] == boosters_map.keys():
        raise HTTPException(status_code=400, detail="The same boosters are indicated in the order")
    add = len(boosters) < len(users)
    if not add:
        for _id in list(set(boosters_map.keys()) - set(users_id)):
            x = await service.get_by_order_id_user_id(order.id, _id)
            await service.delete(x.id)

    for _id, percent in users:
        if _id not in boosters_map.keys():
            if add:
                await service.create(models.UserOrderCreate(
                    order_id=order.id,
                    user_id=_id,
                    dollars=order.price.price_booster_dollar_fee * percent
                ))
        else:
            if not boosters_map[_id].paid:
                await service.update(
                    boosters_map[_id], models.UserOrderUpdate(
                        dollars=order.price.price_booster_dollar_fee * percent
                    )
                )

    boosters = await service.get_by_order_id(order.id)
    booster_str = await service.boosters_to_str(order, boosters)
    await order_service.update_with_sync(order, order_models.OrderUpdate(booster=booster_str))
    return boosters


async def remove_booster(order: order_models.Order, user: User) -> bool:
    boosters = await service.get_by_order_id(order.id)
    for booster in boosters:
        if booster.user_id == user.id:
            await booster.delete()
            p = await service.usd_to_currency(order.price.price_booster_dollar, order.date, with_fee=True)
            price_without = p - booster.dollars
            for booster1 in boosters:
                booster1.dollars += price_without / len(boosters - 1)
                await booster1.save_changes()
            return True
    boosters = await service.get_by_order_id(order.id)
    booster_str = await service.boosters_to_str(order, boosters)
    await order_service.update_with_sync(order, order_models.OrderUpdate(booster=booster_str))
    return False


async def create_user_report(user: User) -> models.UserAccountReport:
    payments = await service.get_by_user_id(user.id)
    orders_id = [p.order_id for p in payments]
    orders = await order_service.get_by_ids(orders_id)
    orders_map: dict[PydanticObjectId, order_models.Order] = {order.id: order for order in orders}
    total, total_rub, paid, paid_rub, not_paid, not_paid_rub, not_paid_orders, paid_orders = 0, 0, 0, 0, 0, 0, 0, 0

    for payment in payments:
        rub = await service.usd_to_currency(
            payment.dollars, orders_map.get(payment.order_id).date, "RUB", with_round=True
        )
        total += payment.dollars
        total_rub += rub
        if payment.paid:
            paid += payment.dollars
            paid_orders += 1
            paid_rub += rub
        else:
            not_paid += payment.dollars
            not_paid_orders += 1
            not_paid_rub += rub

    return models.UserAccountReport(
        total=total,
        total_rub=total_rub,
        paid=paid,
        paid_rub=paid_rub,
        not_paid=not_paid,
        not_paid_rub=not_paid_rub,
        not_paid_orders=not_paid_orders,
        paid_orders=paid_orders
    )


# async def create_report(
#         start_date: datetime,
#         end_date: datetime,
#         first_sort: schemas.FirstSort,
#         second_sort: schemas.SecondSort,
#         spreadsheet: str | None,
#         sheet_id: int | None,
#         username: str | None
# ) -> schemas.AccountingReport:
#     total, total_rub, users, earned = 0, 0, 0, 0
#     items = []
#     if spreadsheet:
#         orders = await order_service.get_all_from_datetime_range_by_sheet(spreadsheet, sheet_id, start_date, end_date)
#     else:
#         orders = await order_service.get_all_from_datetime_range(start_date, end_date)
#     if first_sort.ORDER:
#         orders = sorted(orders, key=lambda x: x.order_id)
#     else:
#         orders = sorted(orders, key=lambda x: x.date)
#     if second_sort.ORDER:
#         orders = sorted(orders, key=lambda x: x.order_id)
#     else:


async def close_order(user: auth_models.User, order: order_service.models.Order, data: models.CloseOrderForm):
    f = False
    for price in await service.get_by_order_id(order.id):
        if price.user_id.id == user.id:
            f = True
    if not f:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail=[{"msg": "You don't have access to the order"}])

    await order_service.update_with_sync(
        order,
        order_service.models.OrderUpdate(screenshot=str(data.url), end_date=datetime.utcnow())
    )
    messages_service.send_order_close_notify(
        auth_models.UserRead.model_validate(user),
        await permissions_service.format_order(order),
        data.url,
        data.message
    )
    return


async def paid_order(user: User, order: order_models.Order) -> models.UserOrder:
    data = await service.get_by_order_id_user_id(order.id, user.id)
    if data.paid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=[{"msg": f"The order has already been paid for {data.paid_time}"}])
    await service.update(data, models.UserOrderUpdate(paid=True))
    boosters = await service.get_by_order_id(order.id)
    if all([booster.paid for booster in boosters]):
        parser = await sheets_service.get_by_spreadsheet_sheet(order.spreadsheet, order.sheet_id)
        user = await auth_service.get_first_superuser()
        tasks_service.update_order.delay(
            user.google.model_dump_json(),
            parser.model_dump_json(),
            order.row_id,
            {"status_paid": "Paid"}
        )
    return data
