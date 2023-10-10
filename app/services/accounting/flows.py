from datetime import datetime

from starlette import status
from tortoise.expressions import Q

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

from . import models, service


async def get_by_order_id_user_id(order: order_service.models.Order, user: auth_models.User) -> models.UserOrder:
    order_user = await service.get_by_order_id_user_id(order.id, user.id)
    if not order_user:
        raise errors.DudeDuckHTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=[errors.DudeDuckException(msg="You are not fulfilling this order", code="not_exist")],
        )
    return order_user


async def get(payment_id: int) -> models.UserOrder:
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
            detail=[errors.DudeDuckException(msg="User is already assigned to this order", code="already_exist")],
        )
    return True


async def order_available(order: order_models.Order) -> bool:
    if order.status == order_models.OrderStatus.Completed:
        raise errors.DudeDuckHTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=[errors.DudeDuckException(msg="You cannot add user to a completed order.", code="cannot_add")],
        )
    if order.status == order_models.OrderStatus.Refund:
        raise errors.DudeDuckHTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=[errors.DudeDuckException(msg="You cannot add user to a refunded order.", code="cannot_add")],
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


async def update_price(order: order_models.Order, price: float, *, user_add: bool = True) -> dict[int, float]:
    boosters = await service.get_by_order_id(order.id)
    await price_collision_fix(order, boosters)
    total_dollars = sum(b.dollars for b in boosters)
    price_map: dict[int, float] = {b.id: b.dollars / total_dollars for b in boosters}
    if user_add:
        price = -price
    for booster in boosters:
        await service.patch(
            booster, user_order_in=models.UserOrderUpdate(dollars=booster.dollars + price * price_map[booster.id])
        )
    if not user_add:
        await price_collision_fix(order, boosters)
    await sync_boosters_sheet(order)
    return price_map


async def price_collision_fix(order: order_models.Order, boosters: list[models.UserOrder]):
    dollars = await currency_flows.usd_to_currency(order.price.price_booster_dollar, order.date, with_fee=True)
    total_dollars = sum(b.dollars for b in boosters)
    free_dollars = dollars - total_dollars
    if free_dollars != 0:
        if len(boosters) > 1:
            price_map: dict[int, float] = {b.id: b.dollars / total_dollars for b in boosters}
            for booster in boosters:
                await service.patch(
                    booster,
                    user_order_in=models.UserOrderUpdate(
                        dollars=booster.dollars + free_dollars * price_map[booster.id]
                    ),
                )
        elif len(boosters) > 0:
            booster = boosters[0]
            await service.patch(booster, user_order_in=models.UserOrderUpdate(dollars=booster.dollars + free_dollars))


async def _add_booster(
    order: order_models.Order,
    user: auth_models.User,
    boosters: list[models.UserOrder],
    price: float,
    method_payment: str | None = None,
    sync: bool = True,
) -> models.UserOrder:
    create_data = models.UserOrderCreate(
        order_id=order.id,
        user_id=user.id,
        dollars=price,
        order_date=order.date,
        completed=True if order.status == order_models.OrderStatus.Completed else False,
        paid=True if order.status_paid == order_models.OrderPaidStatus.Paid else False,
        method_payment=method_payment if method_payment else "$",
    )
    try:
        await update_price(order, price)
        booster = await service.create(order, create_data)
    except Exception as e:
        await update_price(order, price, user_add=False)
        raise e
    if not boosters and sync:
        await order_service.update_with_sync(order, order_models.OrderUpdate(auth_date=datetime.utcnow()))
    await sync_boosters_sheet(order)
    return booster


async def add_booster(
    order: order_models.Order, user: auth_models.User, method_payment: str | None = None, sync: bool = True
) -> models.UserOrder:
    await can_user_pick_order(user, order)
    boosters = await service.get_by_order_id(order.id)
    dollars = await currency_flows.usd_to_currency(order.price.price_booster_dollar, order.date, with_fee=True)
    calculated_dollars = dollars / (len(boosters) + 1)
    return await _add_booster(order, user, boosters, calculated_dollars, method_payment, sync)


async def add_booster_with_price(
    order: order_service.models.Order,
    user: auth_models.User,
    price: float,
    method_payment: str | None = None,
    sync: bool = True,
) -> models.UserOrder:
    await can_user_pick_order(user, order)
    boosters = await service.get_by_order_id(order.id)
    dollars = await currency_flows.usd_to_currency(order.price.price_booster_dollar, order.date, with_fee=True)
    total = sum(b.dollars for b in boosters) + price
    if dollars < price:
        raise errors.DudeDuckHTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=[
                errors.DudeDuckException(
                    msg=f"The price for the booster is incorrect. "
                    f"Order price {dollars}, total price for boosters {total}. \n{total}>{dollars}",
                    code="invalid_price",
                )
            ],
        )
    return await _add_booster(order, user, boosters, price, method_payment, sync)


async def update_booster(order: order_models.Order, user: auth_models.User, update_model: models.UserOrderUpdate):
    boosters = await service.get_by_order_id(order.id)
    boosters_map: dict[int, models.UserOrder] = {b.user_id: b for b in boosters}
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
                await update_price(order, update_model.dollars, user_add=False)
            raise e


async def remove_booster(order: order_models.Order, user: auth_models.User) -> models.UserOrder:
    boosters = await service.get_by_order_id(order.id)
    boosters_map: dict[int, models.UserOrder] = {b.user_id: b for b in boosters}
    to_delete = boosters_map.get(user.id)
    if to_delete is None:
        raise errors.DudeDuckHTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=[errors.DudeDuckException(msg="The user is not a booster of this order", code="not_exist")],
        )
    await service.delete(to_delete.id)
    if len(boosters_map.values()) > 1:
        await update_price(order, to_delete.dollars, user_add=False)
    await sync_boosters_sheet(order)
    return to_delete


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
    start: datetime,
    end: datetime,
    first_sort: models.FirstSort,
    second_sort: models.SecondSort,
    spreadsheet: str | None = None,
    sheet_id: int | None = None,
    username: str | None = None,
    is_completed: bool = True,
    is_paid: bool = False,
) -> models.AccountingReport:
    items: list[models.AccountingReportItem] = []
    completed = order_models.OrderStatus.Completed if is_completed else order_models.OrderStatus.InProgress
    query = [Q(date__gte=start), Q(date__lte=end), Q(status=completed)]

    users_map: dict[int, auth_models.User] = {}
    orders_map: dict[int, order_models.Order] = {}
    payments: list[models.UserOrder] = []
    if sheet_id is not None:
        query.extend([Q(spreadsheet=spreadsheet), Q(sheet_id=sheet_id)])
    if username is None:
        orders_map.update({o.id: o for o in await order_models.Order.filter(*query).prefetch_related("price")})
        payments.extend(await models.UserOrder.filter(order_id__in=orders_map.keys(), paid=is_paid))
        users_map.update({u.id: u for u in await auth_service.get_by_ids([payment.user_id for payment in payments])})
    else:
        chosen_user = await auth_flows.get_booster_by_name(username)
        query.extend([Q(id__in=[p.order_id for p in payments])])
        payments.extend(await models.UserOrder.filter(user_id=chosen_user.id, paid=is_paid))
        users_map.update({chosen_user.id: chosen_user})
        orders_map.update({o.id: o for o in await order_models.Order.filter(*query).prefetch_related("price")})
    total = 0
    earned = 0
    for payment in payments:
        order = orders_map.get(payment.order_id)
        user = users_map.get(payment.user_id)
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
            total += order.price.price_dollar
            earned += payment.dollars
            item = models.AccountingReportItem(
                order_id=order.order_id,
                date=payment.order_date,
                username=user.name,
                dollars=order.price.price_booster_dollar,
                dollars_income=order.price.price_dollar,
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
    return models.AccountingReport(
        total=total,
        orders=await order_models.Order.filter(*query).count(),
        earned=total - earned,
        items=items,
    )


async def close_order(user: auth_models.User, order: order_service.models.Order, data: models.CloseOrderForm):
    f = False
    for price in await service.get_by_order_id(order.id):
        if f := price.user_id == user.id:
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


async def paid_order(payment_id: int) -> models.UserOrder:
    data = await get(payment_id)
    if data.paid:
        raise errors.DudeDuckHTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=[
                errors.DudeDuckException(
                    msg=f"The order has already been paid for {data.paid_at}",
                    code="already_exist",
                )
            ],
        )
    order = await order_flows.get(data.order_id)
    await service.update(data, models.UserOrderUpdate(paid=True))
    boosters = await service.get_by_order_id(order.id)
    if all(booster.paid for booster in boosters):
        await order_service.update_with_sync(
            order, order_models.OrderUpdate(status_paid=order_models.OrderPaidStatus.Paid)
        )
    return data
