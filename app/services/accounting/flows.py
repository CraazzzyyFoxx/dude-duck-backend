import typing
from datetime import datetime

from beanie import PydanticObjectId, WriteRules
from loguru import logger
from starlette import status

from app.core import config, errors
from app.services.auth import flows as auth_flows
from app.services.auth import models as auth_models
from app.services.auth import service as auth_service
from app.services.currency import flows as currency_flows
from app.services.orders import flows as order_flows
from app.services.orders import models as order_models
from app.services.orders import service as order_service
from app.services.permissions import flows as permissions_flows
from app.services.sheets import service as sheets_service
from app.services.tasks import service as tasks_service
from app.services.telegram.message import service as messages_service

from . import models, schemas, service


async def get_by_order_id_user_id(order: order_service.models.Order, user: auth_models.User) -> models.UserOrder:
    order_user = await service.get_by_order_id_user_id(order.id, user.id)
    if not order_user:
        raise errors.DudeDuckHTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=[errors.DudeDuckException(msg="You are not fulfilling this order", code="not_exist")],
        )
    return order_user


async def get(payment_id: PydanticObjectId) -> models.UserOrder:
    order_user = await service.get(payment_id)
    if not order_user:
        raise errors.DudeDuckHTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=[errors.DudeDuckException(msg="Payment doesn't exist", code="not_exist")],
        )
    return order_user


async def check_user_total_orders(user: auth_models.User) -> bool:
    if await service.check_user_total_orders(user):
        return True
    raise errors.DudeDuckHTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=[errors.DudeDuckException(msg="You have reached the limit of active orders.", code="limit_reached")],
    )


async def can_user_pick(user: auth_models.User) -> bool:
    await permissions_flows.can_user_pick(user)
    await check_user_total_orders(user)
    return True


async def can_user_pick_order(user: auth_models.User, order: order_service.models.Order) -> bool:
    await can_user_pick(user)
    order_user = await service.get_by_order_id_user_id(order.id, user.id)
    if order_user:
        raise errors.DudeDuckHTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=[errors.DudeDuckException(msg="You are already assigned to this order", code="already_exist")],
        )
    return True


async def order_available(order: order_models.Order) -> bool:
    if order.status != order_models.OrderStatus.InProgress:
        raise errors.DudeDuckHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[errors.DudeDuckException(msg="You cannot add user to a completed order.", code="cannot_add")],
        )
    return True


async def sync_boosters_sheet(order: order_models.Order) -> None:
    if config.app.sync_boosters:
        parser = await sheets_service.get_by_spreadsheet_sheet_read(order.spreadsheet, order.sheet_id)
        creds = await auth_service.get_first_superuser()
        if creds.google is not None:
            tasks_service.update_order.delay(
                creds.google.model_dump_json(),
                parser.model_dump_json(),
                order.row_id,
                {"booster": await service.boosters_to_str(order, await service.get_by_order_id(order.id))},
            )


async def update_price(order: order_models.Order, price: float, *, add: bool = True) -> dict[PydanticObjectId, float]:
    boosters = await service.get_by_order_id(order.id)
    dollars = await currency_flows.usd_to_currency(order.price.price_booster_dollar, order.date, with_fee=True)
    total_dollars = sum(b.dollars for b in boosters)
    free_dollars = dollars - total_dollars
    price_map: dict[PydanticObjectId, float] = {b.id: b.dollars / (dollars - free_dollars) for b in boosters}
    if add:
        price = -price
    for booster in boosters:
        await booster.inc({"dollars": price * price_map[booster.id]})
    await sync_boosters_sheet(order)
    return price_map


async def _add_booster(
    order: order_models.Order,
    user: auth_models.User,
    create_data: models.UserOrderCreate,
    boosters: list[models.UserOrder],
    price: float,
    sync: bool = True,
) -> models.UserOrder:
    # try:
    #     booster = await service.create(user, order, create_data)
    # except Exception as e:
    #     await update_price(order, price, add=False)
    #     raise e
    booster = await service.create(user, order, create_data)
    if not boosters and sync:
        await order_service.update_with_sync(order, order_models.OrderUpdate(auth_date=datetime.utcnow()))
    await sync_boosters_sheet(order)
    return booster


async def add_booster(order: order_models.Order, user: auth_models.User, sync: bool = True) -> models.UserOrder:
    await can_user_pick(user)
    boosters = await service.get_by_order_id(order.id)
    if user.id in [b.user_id.ref.id for b in boosters]:
        raise errors.DudeDuckHTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=[errors.DudeDuckException(msg="User is already assigned to this order", code="already_exist")],
        )
    dollars = await currency_flows.usd_to_currency(order.price.price_booster_dollar, order.date, with_fee=True)
    calculated_dollars = dollars / (len(boosters) + 1)
    # await update_price(order, calculated_dollars)
    create_data = models.UserOrderCreate(
        order_id=order.id,
        user_id=user.id,
        dollars=calculated_dollars,
        order_date=order.date,
        completed=True if order.status == order_models.OrderStatus.Completed else False,
        paid=True if order.status_paid == order_models.OrderPaidStatus.Paid else False,
    )
    return await _add_booster(order, user, create_data, boosters, calculated_dollars, sync)


async def add_booster_with_price(
    order: order_service.models.Order,
    user: auth_models.User,
    price: float,
    method_payment: str | None = None,
    sync: bool = True,
) -> models.UserOrder:
    await can_user_pick(user)
    boosters = await service.get_by_order_id(order.id)
    if user.id in [b.user_id.ref.id for b in boosters]:
        raise errors.DudeDuckHTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=[errors.DudeDuckException(msg="User is already assigned to this order", code="already_exist")],
        )
    # if len(boosters) == 0:
    #     minus_dollars = 0.0
    # else:
    #     minus_dollars = price / len(boosters)
    p = await currency_flows.usd_to_currency(order.price.price_booster_dollar, order.date, with_fee=True)
    # total = sum([abs(b.dollars - minus_dollars) for b in boosters]) + price
    total = sum(b.dollars for b in boosters) + price
    if p < total:
        raise errors.DudeDuckHTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=[
                errors.DudeDuckException(
                    msg=f"The price for the booster is incorrect. "
                    f"Order price {p}, total price for boosters {total}. \n{total}>{p}",
                    code="invalid_price",
                )
            ],
        )
    # await update_price(order, price)
    create_data = models.UserOrderCreate(
        order_id=order.id,
        user_id=user.id,
        dollars=price,
        order_date=order.date,
        completed=True if order.status == order_models.OrderStatus.Completed else False,
        paid=True if order.status_paid == order_models.OrderPaidStatus.Paid else False,
    )
    if method_payment:
        create_data.method_payment = method_payment
    return await _add_booster(order, user, create_data, boosters, price, sync)


async def update_booster(order: order_models.Order, user: auth_models.User, update_model: models.UserOrderUpdate):
    boosters = await service.get_by_order_id(order.id)
    boosters_map: dict[PydanticObjectId, models.UserOrder] = {b.user_id.ref.id: b for b in boosters}
    if boosters_map.get(user.id) is None:
        raise errors.DudeDuckHTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=[errors.DudeDuckException(msg="The user is not a booster of this order", code="not_exist")],
        )
    else:
        if update_model.dollars is not None:
            await update_price(order, update_model.dollars)
        try:
            return await service.update(boosters_map[user.id], update_model)
        except Exception as e:
            if update_model.dollars is not None:
                await update_price(order, update_model.dollars, add=False)
            raise e


async def remove_booster(order: order_models.Order, user: auth_models.User) -> models.UserOrder:
    boosters = await service.get_by_order_id(order.id)
    boosters_map: dict[PydanticObjectId, models.UserOrder] = {b.user_id.ref.id: b for b in boosters}
    to_delete = boosters_map.get(user.id)
    if to_delete is None:
        raise errors.DudeDuckHTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=[errors.DudeDuckException(msg="The user is not a booster of this order", code="not_exist")],
        )
    await service.delete(to_delete.id)
    if len(boosters_map.values()) > 1:
        await update_price(order, to_delete.dollars, add=False)
    await sync_boosters_sheet(order)
    return to_delete


# async def update_boosters_percent(
#     order: order_service.models.Order, data: models.SheetUserOrderCreate
# ) -> list[models.UserOrder]:
#     users: list[tuple[PydanticObjectId, float]] = []
#     users_id = []
#     for item in data.items:
#         user = await auth_flows.get_booster_by_name(item.username)
#         users.append((user.id, item.percent))
#         users_id.append(user.id)
#
#     boosters = await service.get_by_order_id(order.id)
#     boosters_map = {booster.user_id: booster for booster in boosters}
#     if [u[0] for u in users] == boosters_map.keys():
#         raise errors.DudeDuckHTTPException(
#             status_code=400,
#             detail=[errors.DudeDuckException(msg="The same boosters are indicated in the order", code="already_exist")],
#         )
#     add = len(boosters) < len(users)
#     if not add:
#         for _id in set(boosters_map.keys()) - set(users_id):
#             x = await get_by_order_id_user_id(order, boosters_map[_id])
#             await service.delete(x.id)
#
#     for _id, percent in users:
#         dollars = await currency_flows.usd_to_currency(order.price.price_booster_dollar, order.date, with_fee=True)
#         dollars *= percent
#         if _id not in boosters_map.keys() and add:
#             created = models.UserOrderCreate(order_id=order.id, user_id=_id, dollars=dollars, order_date=order.date)
#             await service.create(order, user, created)
#         elif not boosters_map[_id].paid:
#             await service.update(boosters_map[_id], models.UserOrderUpdate(dollars=dollars))
#
#     boosters = await service.get_by_order_id(order.id)
#     return boosters


async def create_user_report(user: auth_models.User) -> models.UserAccountReport:
    payments = await service.get_by_user_id(user.id)
    total: float = 0.0
    total_rub: float = 0.0
    paid: float = 0.0
    paid_rub: float = 0.0
    not_paid: float = 0.0
    not_paid_rub: float = 0.0
    not_paid_orders: int = 0
    paid_orders: int = 0

    for payment in payments:
        rub = await currency_flows.usd_to_currency(payment.dollars, payment.order_date, "RUB", with_round=True)
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
        paid_orders=paid_orders,
    )


async def create_report(
    start_date: datetime,
    end_date: datetime,
    first_sort: schemas.FirstSort,
    second_sort: schemas.SecondSort,
    spreadsheet: str | None = None,
    sheet_id: int | None = None,
    username: str | None = None,
) -> schemas.AccountingReport:
    items: list[schemas.AccountingReportItem] = []
    if username is None:
        query: dict[str, typing.Any] = {"date": {"$gte": start_date, "$lte": end_date}}
        if sheet_id is not None:
            query.update({"spreadsheet": spreadsheet, "sheet_id": sheet_id})
        orders = await order_models.Order.find(query).to_list()
        orders_map: dict[PydanticObjectId, order_models.Order] = {o.id: o for o in orders}
        payments = await service.get_by_orders(list(orders_map.keys()))
        user_ids: list[PydanticObjectId] = [payment.user_id.ref.id for payment in payments]
        users = await auth_service.get_by_ids(user_ids)
        users_map: dict[PydanticObjectId, auth_models.User] = {u.id: u for u in users}
    else:
        chosen_user = await auth_flows.get_booster_by_name(username)
        payments = await service.get_by_user_id(chosen_user.id)
        users_map = {chosen_user.id: chosen_user}
        query: dict[str, typing.Any] = {
            "_id": {"$in": [p.order_id for p in payments]},
            "date": {"$gte": start_date, "$lte": end_date},
        }
        if sheet_id is not None:
            query.update(
                {
                    "spreadsheet": spreadsheet,
                    "sheet_id": sheet_id,
                }
            )
        orders = await order_models.Order.find(query).to_list()
        orders_map: dict[PydanticObjectId, order_models.Order] = {order.id: order for order in orders}

    for payment in payments:
        order = orders_map.get(payment.order_id.ref.id)
        user = users_map.get(payment.user_id.ref.id)
        if order and user:
            if user.binance_id:
                payment_str: str = str(user.binance_id)
                bank: str = "Binance ID"
            elif user.binance_email:
                payment_str: str = user.binance_email
                bank: str = "Binance Email"
            elif user.phone:
                payment_str: str = user.phone
                bank: str = user.bank
            elif user.bankcard:
                payment_str: str = user.phone
                bank: str = user.bank
            else:
                payment_str: str = "Хуй знает"
                bank: str = "Хуй знает"

            rub = await currency_flows.usd_to_currency(payment.dollars, payment.order_date, currency="RUB")
            item = schemas.AccountingReportItem(
                order_id=order.order_id,
                date=payment.order_date,
                username=user.name,
                dollars=order.price.price_dollar,
                rub=rub,
                dollars_fee=payment.dollars,
                end_date=order.end_date,
                payment=payment_str,
                bank=bank,
                status=order.status,
                payment_id=payment.id,
            )
            items.append(item)

    if first_sort.ORDER:
        items = sorted(items, key=lambda x: (x.order_id[0], int(x.order_id[1:])))
    else:
        items = sorted(items, key=lambda x: x.date)
    if second_sort.ORDER:
        items = sorted(items, key=lambda x: (x.order_id[0], int(x.order_id[1:])))
    else:
        items = sorted(items, key=lambda x: x.username)
    total = await order_models.Order.find(query).sum(order_models.Order.price.price_dollar)  # type: ignore
    earned = await order_models.Order.find(query).sum(order_models.Order.price.price_booster_dollar)  # type: ignore
    if earned is None:
        earned = 0.0
    return schemas.AccountingReport(
        total=total,
        orders=await order_models.Order.find(query).count(),
        earned=total - earned,
        items=items,
    )


async def close_order(user: auth_models.User, order: order_service.models.Order, data: models.CloseOrderForm):
    f = False
    for price in await service.get_by_order_id(order.id):
        if f := price.user_id.ref.id == user.id:
            break
    if not f:
        raise errors.DudeDuckHTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=[errors.DudeDuckException(msg="You don't have access to the order", code="forbidden")],
        )
    update_model = order_service.models.OrderUpdate(screenshot=str(data.url), end_date=datetime.utcnow())
    new_order = await order_service.update_with_sync(order, update_model)
    messages_service.send_order_close_notify(
        auth_models.UserRead.model_validate(user), order.order_id, str(data.url), data.message
    )
    return new_order


async def paid_order(payment_id: PydanticObjectId) -> models.UserOrder:
    data = await get(payment_id)
    if data.paid:
        raise errors.DudeDuckHTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=[
                errors.DudeDuckException(
                    msg=f"The order has already been paid for {data.paid_time}",
                    code="already_exist",
                )
            ],
        )
    order = await order_flows.get(data.order_id.ref.id)
    await service.update(data, models.UserOrderUpdate(paid=True))
    boosters = await service.get_by_order_id(order.id)
    if all(booster.paid for booster in boosters):
        await order_service.update_with_sync(
            order, order_models.OrderUpdate(status_paid=order_models.OrderPaidStatus.Paid)
        )
    return data
