from datetime import datetime

from fastapi import HTTPException
from loguru import logger
from starlette import status
from beanie.odm.operators.find.comparison import In

from app.services.auth.models import User
from app.services.auth import service as auth_service
from app.services.orders import service as order_service
from app.services.orders import flows as order_flows
from app.services.messages import service as messages_service

from . import models, service


async def check_user_total_orders(user: auth_service.models.User) -> bool:
    if await service.check_user_total_orders(user):
        return True
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                        detail=[
                            {
                                "msg": "You have reached the limit of active orders."
                            }
                        ])


async def can_user_pick(user: auth_service.models.User) -> bool:
    if not user.is_verified:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail=[
                                {
                                    "msg": "Only verified users can fulfill orders"
                                }
                            ])
    await check_user_total_orders(user)
    return True


async def add_booster(order: order_service.models.Order, user: auth_service.models.User) -> models.UserOrder:
    await service.can_user_pick(user)
    boosters = await service.get_by_order_id(order.id)
    percent = 100 / len(boosters) + 1
    price = order.price_booster_dollar_fee * percent
    for booster in boosters:
        await service.update(booster, models.UserOrderUpdate(dollars=price))

    data = await service.create(models.UserOrderCreate(order_id=order.id, user_id=user.id, dollars=price))
    booster = await service.boosters_to_str(order, [data, *boosters])
    await order_service.update_with_sync(order, order_service.models.OrderUpdate(booster=booster))
    return data


async def update_boosters_percent(data: models.SheetUserOrderCreate) -> list[models.UserOrder]:
    order = await order_flows.get_by_order_id(data.order_id)

    users = []
    for item in data.items:
        user = await auth_service.get_booster_by_name(item.username)
        users.append((user.id, item.percent))

    boosters = await service.get_by_order_id(order.id)
    count = 0
    for booster in boosters:
        for d in users:
            if booster.user.id == d[0]:
                break
        else:
            count += 1

    if not count == 0 and count != 1:
        raise HTTPException(status_code=400, detail=[
                                {
                                    "msg": "You can add or remove only one user per operation"
                                }
                            ])
    need = None
    if add := True if len(boosters) < len(users) else False:
        for user in users:
            if user[0] not in [b.id for b in boosters]:
                need = user[0]
    else:
        for booster in boosters:
            if booster.user.id not in [b[0] for b in users]:
                need = booster.user.id

    if add:
        for user in users:
            if user[0] == need:
                await models.UserOrder(order_id=order.id, user_id=need,
                                       dollars=order.price.price_booster_dollar_fee * user[1]).create()
            for booster in boosters:
                if user[0] == booster.user_id:  # TODO: Add check paid
                    booster.dollars = order.price.price_booster_dollar_fee * user[1]
                    await booster.save_changes()
    else:
        for booster in boosters:
            for d in users:
                if booster.user.id == need:
                    await booster.delete()
                if booster.user.id == d[0]:
                    booster.dollars = order.price.price_booster_dollar_fee * d[1]
                    await booster.save_changes()
    data = await service.get_by_order_id(order.id)
    booster = await service.boosters_to_str(order, data)
    await order_service.update_with_sync(order, order_service.models.OrderUpdate(booster=booster))
    return data


async def remove_booster(user: User, order: models.Order) -> bool:
    boosters = await service.get_by_order_id(order.id)
    for booster in boosters:
        if booster.user_id == user.id:
            price_without = order.price_booster_dollar_fee - booster.dollars
            for booster1 in boosters:
                booster1.dollars += price_without / len(boosters)
                await booster1.save_changes()
            await booster.delete()
            return True

    return False


async def create_user_report(user: User) -> models.UserAccountReport:
    payments = await service.get_by_user_id(user.id)
    orders = await models.Order.find(In(models.Order.id, [p.order.id for p in payments]), fetch_links=True).to_list()
    orders_map = {order.id: order for order in orders}
    total: float = 0
    total_rub: float = 0
    paid: float = 0
    paid_rub: float = 0
    not_paid: float = 0
    not_paid_rub: float = 0
    not_paid_orders: int = 0
    paid_orders: int = 0

    for payment in payments:
        total += service.calculate_price_dollars(payment.dollars)
        total_rub += service.calculate_price_rub(payment.dollars, orders_map.get(payment.order.id).exchange)
        if payment.paid:
            paid += service.calculate_price_dollars(payment.dollars)
            paid_orders += 1
            paid_rub += service.calculate_price_rub(payment.dollars, orders_map.get(payment.order.id).exchange)
        else:
            not_paid += service.calculate_price_dollars(payment.dollars)
            not_paid_orders += 1
            not_paid_rub += service.calculate_price_rub(payment.dollars, orders_map.get(payment.order.id).exchange)

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


#
# async def create_report(
#         start_date: datetime,
#         end_date: datetime,
#         first_sort: schemas.FirstSort,
#         second_sort: schemas.SecondSort,
#         spreadsheet: str,
#         sheet_id: int | None,
#         username: str | None
# ) -> schemas.AccountingReport:
#     total = 0
#     total_rub = 0
#     users = 0
#     orders = 0
#     earned = 0
#     items = []
#     if spreadsheet:
#         orders = order_service.get_all_from_datetime_range_by_sheet(spreadsheet, sheet_id, start_date, end_date)


async def close_order(user: auth_service.models.User, order: order_service.models.Order, data: models.CloseOrderForm):
    f = False
    for price in await service.get_by_order_id(order.id):
        if price.user.id == user.id:
            f = True
    if not f:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=[
            {
                "msg": f"You don't have access to the order"
            }
        ])

    await order_service.update_with_sync(order, order_service.models.OrderUpdate(
        screenshot=str(data.url), end_date=datetime.utcnow()))
    await messages_service.send_order_close_request(user, order, data.url, data.message)
    return


async def paid_order(user: User, order: models.Order) -> models.UserOrder:
    data = await service.get_by_order_id_user_id(order.id, user.id)
    if data.paid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=[
                                {
                                    "msg": f"The order has already been paid for {data.paid_time}"
                                }
                            ])
    await service.update(data, models.UserOrderUpdate(paid=True))
    boosters = await service.get_by_order_id(order.id)
    if all([booster.paid for booster in boosters]):
        await order_service.update_with_sync(order, order_service.models.OrderUpdate(status_paid="Paid"))
    return data
