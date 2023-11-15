import sqlalchemy as sa

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from sqlalchemy.sql.functions import count
from starlette import status

from src.core import errors, pagination
from src.services.accounting import models as accounting_models
from src.services.currency import flows as currency_flows

from . import models, schemas, service


async def get(session: AsyncSession, order_id: int) -> models.Order:
    order = await service.get(session, order_id)
    if not order:
        raise errors.DDHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[errors.DDException(msg="A order with this id does not exist.", code="not_exist")],
        )
    return order


async def get_by_order_id(session: AsyncSession, order_id: str) -> models.Order:
    order = await service.get_order_id(session, order_id)
    if not order:
        raise errors.DDHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[
                errors.DDException(msg=f"A order with this id does not exist. [order_id={order_id}]", code="not_exist")
            ],
        )
    return order


async def create(session: AsyncSession, order_in: models.OrderCreate) -> models.Order:
    order = await service.get_order_id(session, order_in.order_id)
    if order:
        raise errors.DDHTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=[
                errors.DDException(
                    msg=f"A order with this id already exist. [order_id={order_in.order_id}]", code="already_exist"
                )
            ],
        )
    order = await service.create(session, order_in)
    return order


async def format_order_system(session: AsyncSession, order: models.Order):
    data = order.to_dict()
    booster_price = order.price.booster_dollar_fee
    price = schemas.OrderPriceSystem(
        dollar=order.price.dollar,
        booster_dollar_fee=booster_price,
        booster_dollar=order.price.booster_dollar,
        booster_rub=await currency_flows.usd_to_currency(session, booster_price, order.date, "RUB"),
        booster_gold=order.price.booster_gold,
    )
    data["price"] = price
    data["info"] = order.info.to_dict()
    data["credentials"] = order.credentials.to_dict()
    return schemas.OrderReadSystem.model_validate(data)


async def format_order_perms(
        session: AsyncSession, order: models.Order, *, has: bool = False
) -> schemas.OrderReadNoPerms | schemas.OrderReadHasPerms:
    data = order.to_dict()
    booster_price = order.price.booster_dollar_fee
    price = schemas.OrderPriceUser(
        booster_dollar=order.price.booster_dollar,
        booster_dollar_fee=booster_price,
        booster_rub=await currency_flows.usd_to_currency(session, booster_price, order.date, "RUB"),
        booster_gold=order.price.booster_gold,
    )
    data["price"] = price
    data["info"] = order.info.to_dict()
    data["credentials"] = order.credentials.to_dict()
    if has:
        return schemas.OrderReadHasPerms.model_validate(data)
    return schemas.OrderReadNoPerms.model_validate(data)


async def format_order_active(session: AsyncSession, order: models.Order, order_active: accounting_models.UserOrder):
    data = order.to_dict()

    price = schemas.OrderPriceUser(
        booster_dollar=order.price.booster_dollar,
        booster_dollar_fee=order_active.dollars,
        booster_rub=await currency_flows.usd_to_currency(session, order_active.dollars, order.date, "RUB"),
        booster_gold=order.price.booster_gold,
    )
    data["price"] = price
    data["paid_at"] = order_active.paid_at
    data["info"] = order.info.to_dict()
    data["credentials"] = order.credentials.to_dict()
    return schemas.OrderReadActive.model_validate(data)


async def get_by_filter(
    session: AsyncSession, params: schemas.OrderFilterParams, *, has: bool = False
) -> pagination.Paginated[schemas.OrderReadNoPerms | schemas.OrderReadHasPerms]:  # noqa
    query = (
        sa.select(models.Order)
        .options(joinedload(models.Order.info), joinedload(models.Order.price), joinedload(models.Order.credentials))
        .offset(params.offset)
        .limit(params.limit)
        .order_by(params.order_by)
    )

    if params.order_id and not params.ids:
        query = query.where(models.Order.order_id.in_(params.order_id))
    elif params.ids and not params.order_id:
        query = query.where(models.Order.id.in_(params.ids))
    else:
        query = query.where(models.Order.order_id.in_(params.order_id) | models.Order.id.in_(params.ids))

    if params.status != schemas.OrderStatusFilter.All:
        query = query.where(models.Order.status == models.OrderStatus(params.status))

    result = await session.execute(query)
    results = [await format_order_perms(session, order, has=has) for order in result.scalars()]
    total = await session.execute(sa.select(count(models.Order.id)))
    return pagination.Paginated(page=params.page, per_page=params.per_page, total=total.first()[0], results=results)
