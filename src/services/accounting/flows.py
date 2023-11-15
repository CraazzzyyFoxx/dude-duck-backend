from datetime import datetime, UTC

import sqlalchemy as sa

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from sqlalchemy.sql.functions import count
from starlette import status

from src.core import errors, pagination
from src.services.auth import models as auth_models
from src.services.currency import flows as currency_flows
from src.services.order import flows as order_flows
from src.services.order import models as order_models
from src.services.order import service as order_service
from src.services.order import schemas as order_schemas
from src.services.permissions import flows as permissions_flows
from src.services.telegram.message import service as messages_service

from . import models, service


async def get_by_order_id_user_id(
    session: AsyncSession, order: order_models.Order, user: auth_models.User
) -> models.UserOrder:
    order_user = await service.get_by_order_id_user_id(session, order.id, user.id)
    if not order_user:
        raise errors.DDHTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=[errors.DDException(msg="You are not fulfilling this order", code="not_exist")],
        )
    return order_user


async def get(session: AsyncSession, payment_id: int) -> models.UserOrder:
    order_user = await service.get(session, payment_id)
    if not order_user:
        raise errors.DDHTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=[errors.DDException(msg="Payment doesn't exist", code="not_exist")],
        )
    return order_user


async def check_user_total_orders(session: AsyncSession, user: auth_models.User) -> bool:
    if await service.check_user_total_orders(session, user):
        return True
    raise errors.DDHTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=[errors.DDException(msg="You have reached the limit of active orders.", code="limit_reached")],
    )


async def can_user_pick(session: AsyncSession, user: auth_models.User) -> bool:
    await permissions_flows.can_user_pick(user)
    await check_user_total_orders(session, user)
    return True


async def can_user_pick_order(session: AsyncSession, user: auth_models.User, order: order_models.Order) -> bool:
    await can_user_pick(session, user)
    order_user = await service.get_by_order_id_user_id(session, order.id, user.id)
    if order_user:
        raise errors.DDHTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=[errors.DDException(msg="User is already assigned to this order", code="already_exist")],
        )
    return True


async def add_booster(
    session: AsyncSession,
    order: order_models.Order,
    user: auth_models.User,
    method_payment: str | None = None,
    sync: bool = True,
) -> models.UserOrder:
    await can_user_pick_order(session, user, order)
    boosters = await service.get_by_order_id(session, order.id)
    calculated_dollars = order.price.booster_dollar_fee / (len(boosters) + 1)
    return await service.create(session, order, user, boosters, calculated_dollars, method_payment, sync)


async def add_booster_with_price(
    session: AsyncSession,
    order: order_models.Order,
    user: auth_models.User,
    price: float,
    method_payment: str | None = None,
    sync: bool = True,
) -> models.UserOrder:
    await can_user_pick_order(session, user, order)
    boosters = await service.get_by_order_id(session, order.id)
    dollars = order.price.booster_dollar_fee
    total = sum(b.dollars for b in boosters) + price
    if dollars < price:
        raise errors.DDHTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=[
                errors.DDException(
                    msg=f"The price for the booster is incorrect. "
                    f"Order price {dollars}, total price for boosters {total}. \n{total}>{dollars}",
                    code="invalid_price",
                )
            ],
        )
    return await service.create(session, order, user, boosters, price, method_payment, sync)


async def create_user_report(session: AsyncSession, user: auth_models.User) -> models.UserAccountReport:
    result = await session.scalars(sa.select(models.UserOrder).filter_by(user_id=user.id, completed=True))
    total: float = 0.0
    total_rub: float = 0.0
    paid: float = 0.0
    paid_rub: float = 0.0
    not_paid: float = 0.0
    not_paid_rub: float = 0.0
    not_paid_orders: int = 0
    paid_orders: int = 0

    for payment in result.all():
        rub = await currency_flows.usd_to_currency(session, payment.dollars, payment.order_date, "RUB", with_round=True)
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
    session: AsyncSession,
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
    query = (
        sa.select(order_models.Order, models.UserOrder, auth_models.User)
        .where(order_models.Order.date >= start, order_models.Order.date <= end)
        .where(models.UserOrder.completed == is_completed, models.UserOrder.paid == is_paid)
        .options(joinedload(order_models.Order.price))
        .order_by(order_models.Order.date)
    )
    if sheet_id is not None:
        query = query.where(order_models.Order.sheet_id == sheet_id, order_models.Order.spreadsheet == spreadsheet)
    query = query.join(models.UserOrder, order_models.Order.id == models.UserOrder.order_id).join(
        auth_models.User, models.UserOrder.user_id == auth_models.User.id
    )
    if username is not None:
        query = query.where(auth_models.User.name == username)
    count: int = 0
    total = 0.0
    earned = 0.0
    for row in await session.execute(query):
        count += 1
        order: order_models.Order = row[0]
        payment: models.UserOrder = row[1]
        user: auth_models.User = row[2]
        if order and user:
            payment_str: str = "Хуй знает"
            bank: str = "Хуй знает"
            if user.binance_id:
                payment_str = str(user.binance_id)
                bank = "Binance ID"
            elif user.binance_email:
                payment_str = str(user.binance_email)
                bank = "Binance Email"
            elif user.phone and user.bank:
                payment_str = user.phone
                bank = user.bank
            elif user.bankcard and user.bank:
                payment_str = user.bankcard
                bank = user.bank

            total += order.price.dollar
            earned += payment.dollars
            item = models.AccountingReportItem(
                order_id=order.order_id,
                date=payment.order_date,
                username=user.name,
                dollars=order.price.booster_dollar,
                dollars_income=order.price.dollar,
                rub=await currency_flows.usd_to_currency(session, payment.dollars, payment.order_date, "RUB"),
                dollars_fee=payment.dollars,
                end_date=order.end_date,
                payment=payment_str,
                bank=bank,
                status=order.status,
                payment_id=payment.id,
            )
            items.append(item)

    if first_sort == models.FirstSort.ORDER:
        items = sorted(items, key=lambda x: (x.order_id[0], int(x.order_id[1:])))
    else:
        items = sorted(items, key=lambda x: x.date)
    if second_sort == models.SecondSort.ORDER:
        if first_sort == models.FirstSort.ORDER:
            items = sorted(items, key=lambda x: (x.order_id[0], int(x.order_id[1:])))
    else:
        items = sorted(items, key=lambda x: x.username)
    return models.AccountingReport(total=total, orders=count, earned=total - earned, items=items)


async def close_order(
    session: AsyncSession, user: auth_models.User, order: order_models.Order, data: models.CloseOrderForm
) -> order_models.Order:
    f = False
    for price in await service.get_by_order_id(session, order.id):
        if f := price.user_id == user.id:
            break
    if not f:
        raise errors.DDHTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=[errors.DDException(msg="You don't have access to the order", code="forbidden")],
        )
    update_model = order_models.OrderUpdate(screenshot=str(data.url), end_date=datetime.now(tz=UTC))
    new_order = await order_service.update_with_sync(session, order, update_model)
    messages_service.send_order_close_notify(
        auth_models.UserRead.model_validate(user), order.order_id, str(data.url), data.message
    )
    return new_order


async def paid_order(session: AsyncSession, payment_id: int) -> models.UserOrder:
    data = await get(session, payment_id)
    if data.paid:
        raise errors.DDHTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=[
                errors.DDException(
                    msg=f"The order has already been paid for {data.paid_at}",
                    code="already_exist",
                )
            ],
        )
    order = await order_flows.get(session, data.order_id)
    await service.patch(session, data, models.UserOrderUpdate(paid=True))
    boosters = await service.get_by_order_id(session, order.id)
    if all(booster.paid for booster in boosters):
        await order_service.update_with_sync(
            session, order, order_models.OrderUpdate(status_paid=order_models.OrderPaidStatus.Paid)
        )
    return data


async def get_by_filter(
    session: AsyncSession, params: models.UserOrderFilterParams
) -> pagination.Paginated[order_schemas.OrderReadActive]:
    query = (
        sa.select(order_models.Order, models.UserOrder)
        .where(models.UserOrder.user_id == params.user_id, order_models.Order.status == params.status)
        .options(
            joinedload(order_models.Order.info),
            joinedload(order_models.Order.price),
            joinedload(order_models.Order.credentials)
        )
        .offset(params.offset)
        .limit(params.limit)
        .order_by(params.order_by)
    )
    result = await session.execute(query)
    results = []
    for row in result:
        order: order_models.Order = row[0]
        user_order: models.UserOrder = row[1]
        results.append(await order_flows.format_order_active(session, order, user_order))
    total = await session.execute(sa.select(count(models.UserOrder.id)).filter_by(user_id=params.user_id))
    return pagination.Paginated(page=params.page, per_page=params.per_page, total=total.first()[0], results=results)
