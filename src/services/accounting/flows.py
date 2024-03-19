from datetime import UTC, date, datetime

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from sqlalchemy.sql.functions import count
from starlette import status

from src import models, schemas
from src.core import errors, pagination
from src.services.auth import flows as auth_flows
from src.services.currency import flows as currency_flows
from src.services.integrations.notifications import flows as notifications_flows
from src.services.integrations.sheets import flows as sheets_flows
from src.services.order import flows as order_flows
from src.services.order import service as order_service
from src.services.payroll import service as payroll_service
from src.services.permissions import flows as permissions_flows
from src.services.screenshot import service as screenshot_service

from . import service


async def get_by_order_id_user_id(session: AsyncSession, order: models.Order, user: models.User) -> models.UserOrder:
    order_user = await service.get_by_order_id_user_id(session, order.id, user.id)
    if not order_user:
        raise errors.ApiHTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=[errors.ApiException(msg="You are not fulfilling this order", code="not_exist")],
        )
    return order_user


async def get(session: AsyncSession, payment_id: int) -> models.UserOrder:
    order_user = await service.get(session, payment_id)
    if not order_user:
        raise errors.ApiHTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=[errors.ApiException(msg="Payment doesn't exist", code="not_exist")],
        )
    return order_user


async def check_user_total_orders(session: AsyncSession, user: models.User) -> bool:
    if await service.check_user_total_orders(session, user):
        return True
    raise errors.ApiHTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=[errors.ApiException(msg="You have reached the limit of active orders.", code="limit_reached")],
    )


async def can_user_pick(session: AsyncSession, user: models.User) -> bool:
    await permissions_flows.can_user_pick(user)
    await check_user_total_orders(session, user)
    return True


async def can_user_pick_order(session: AsyncSession, user: models.User, order: models.Order) -> bool:
    await can_user_pick(session, user)
    order_user = await service.get_by_order_id_user_id(session, order.id, user.id)
    if order_user:
        raise errors.ApiHTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=[errors.ApiException(msg="User is already assigned to this order", code="already_exist")],
        )
    return True


async def add_booster(
    session: AsyncSession,
    order: models.Order,
    user: models.User,
    sync: bool = True,
) -> models.UserOrder:
    await can_user_pick_order(session, user, order)
    boosters = await service.get_by_order_id(session, order.id)
    calculated_dollars = order.price.booster_dollar_fee / (len(boosters) + 1)
    return await service.create(session, order, user, boosters, calculated_dollars, sync)


async def add_booster_with_price(
    session: AsyncSession,
    order: models.Order,
    user: models.User,
    price: float,
    sync: bool = True,
) -> models.UserOrder:
    await can_user_pick_order(session, user, order)
    boosters = await service.get_by_order_id(session, order.id)
    dollars = order.price.booster_dollar_fee
    total = sum(b.dollars for b in boosters) + price
    if dollars < price:
        raise errors.ApiHTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=[
                errors.ApiException(
                    msg=f"The price for the booster is incorrect. "
                    f"Order price {dollars}, total price for boosters {total}. \n{total}>{dollars}",
                    code="invalid_price",
                )
            ],
        )
    return await service.create(session, order, user, boosters, price, sync)


async def create_user_report(session: AsyncSession, user: models.User) -> schemas.UserAccountReport:
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

    return schemas.UserAccountReport(
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
    start: datetime | date,
    end: datetime | date,
    first_sort: schemas.FirstSort,
    second_sort: schemas.SecondSort,
    spreadsheet: str | None = None,
    sheet_id: int | None = None,
    username: str | None = None,
    is_completed: bool = True,
    is_paid: bool = False,
) -> schemas.AccountingReport:
    items: list[schemas.AccountingReportItem] = []
    query = (
        sa.select(models.Order, models.UserOrder, models.User)
        .where(models.Order.date >= start, models.Order.date <= end)
        .where(models.UserOrder.completed == is_completed, models.UserOrder.paid == is_paid)
        .options(joinedload(models.Order.price))
        .order_by(models.Order.date)
    )
    if sheet_id is not None:
        query = query.where(
            models.Order.sheet_id == sheet_id,
            models.Order.spreadsheet == spreadsheet,
        )
    query = query.join(models.UserOrder, models.Order.id == models.UserOrder.order_id).join(
        models.User, models.UserOrder.user_id == models.User.id
    )
    if username is not None:
        query = query.where(models.User.name == username)
    count_orders: int = 0
    total = 0.0
    earned = 0.0
    for row in await session.execute(query):
        count_orders += 1
        order: models.Order = row[0]
        payment: models.UserOrder = row[1]
        user: models.User = row[2]
        if order and user:
            payroll = await payroll_service.get_by_priority(session, user)
            total += order.price.dollar
            earned += payment.dollars
            item = schemas.AccountingReportItem(
                order_id=order.order_id,
                date=payment.order_date,
                username=user.name,
                dollars=order.price.booster_dollar,
                dollars_income=order.price.dollar,
                rub=await currency_flows.usd_to_currency(session, payment.dollars, payment.order_date, "RUB"),
                dollars_fee=payment.dollars,
                end_date=order.end_date,
                payment=payroll.value,
                bank=f"{payroll.type} - {payroll.bank}",
                status=order.status,
                payment_id=payment.id,
            )
            items.append(item)

    if first_sort == schemas.FirstSort.ORDER:
        items = sorted(items, key=lambda x: (x.order_id[0], int(x.order_id[1:])))
    else:
        items = sorted(items, key=lambda x: x.date)
    if second_sort == schemas.SecondSort.ORDER:
        if first_sort == schemas.FirstSort.ORDER:
            items = sorted(items, key=lambda x: (x.order_id[0], int(x.order_id[1:])))
    else:
        items = sorted(items, key=lambda x: x.username)
    return schemas.AccountingReport(total=total, orders=count_orders, earned=total - earned, items=items)


async def close_order(
    session: AsyncSession,
    user: models.User,
    order: models.Order,
    data: schemas.CloseOrderForm,
) -> models.Order:
    if await service.get_by_order_id_user_id(session, order.id, user.id) is None:
        raise errors.ApiHTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=[errors.ApiException(msg="You don't have access to the order", code="forbidden")],
        )
    await screenshot_service.create(session, user, order, data.url.unicode_string())
    update_model = schemas.OrderUpdate(end_date=datetime.now(tz=UTC))
    new_order = await order_service.update(session, order, update_model)
    await sheets_flows.order_to_sheets(session, new_order, await order_flows.format_order_system(session, new_order))
    notifications_flows.send_order_close_notify(
        schemas.UserRead.model_validate(user),
        order.order_id,
        str(data.url),
        data.message,
    )
    return new_order


async def paid_order(session: AsyncSession, payment_id: int) -> models.UserOrder:
    data = await get(session, payment_id)
    if data.paid:
        raise errors.ApiHTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=[
                errors.ApiException(
                    msg=f"The order has already been paid for {data.paid_at}",
                    code="already_exist",
                )
            ],
        )
    order = await order_flows.get(session, data.order_id)
    user = await auth_flows.get(session, data.user_id)
    await service.update(session, order, user, schemas.UserOrderUpdate(paid=True), patch=True)
    boosters = await service.get_by_order_id(session, order.id)
    if all(booster.paid for booster in boosters):
        update_model = schemas.OrderUpdate(status_paid=models.OrderPaidStatus.Paid)
        new_order = await order_service.update(session, order, update_model)
        await sheets_flows.order_to_sheets(
            session,
            new_order,
            await order_flows.format_order_system(session, new_order),
        )
    return data


async def get_by_filter(
    session: AsyncSession,
    user: models.User,
    params: schemas.OrderFilterParams,
) -> pagination.Paginated[schemas.OrderReadActive]:
    query = (
        sa.select(models.UserOrder, models.Order)
        .where(models.UserOrder.user_id == user.id)
        .join(
            models.Order,
            models.UserOrder.order_id == models.Order.id,
            isouter=True,
        )
        .options(
            joinedload(models.Order.info),
            joinedload(models.Order.price),
            joinedload(models.Order.credentials),
            joinedload(models.Order.screenshots),
        )
    )
    query = params.apply_filters(query)
    query = params.apply_pagination(query)
    result = await session.execute(query)
    results = []
    count_query = (
        sa.select(count(models.UserOrder.id))
        .join(models.Order, models.Order.id == models.UserOrder.order_id)
        .where(models.UserOrder.user_id == user.id)
    )
    count_query = params.apply_filters(count_query)
    total = await session.execute(count_query)
    for row in result.unique():
        user_order: models.UserOrder = row[0]
        order: models.Order = row[1]
        results.append(await order_flows.format_order_active(session, order, user_order))
    return pagination.Paginated(
        page=params.page,
        per_page=params.per_page,
        total=total.one()[0],
        results=results,
    )
