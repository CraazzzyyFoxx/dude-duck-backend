import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from sqlalchemy.sql.functions import count
from starlette import status

from src import models, schemas
from src.core import errors, pagination
from src.services.currency import flows as currency_flows

from . import service


async def get(session: AsyncSession, order_id: int) -> models.PreOrder:
    order = await service.get(session, order_id)
    if not order:
        raise errors.ApiHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[errors.ApiException(msg="A preorder with this id does not exist.", code="not_exist")],
        )
    return order


async def get_by_order_id(session: AsyncSession, order_id: str) -> models.PreOrder:
    order = await service.get_order_id(session, order_id)
    if not order:
        raise errors.ApiHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[errors.ApiException(msg="A preorder with this id does not exist.", code="not_exist")],
        )
    return order


async def create(session: AsyncSession, order_in: schemas.PreOrderCreate) -> models.PreOrder:
    order = await service.create(session, order_in)
    return order


async def delete(session: AsyncSession, order_id: int) -> None:
    await service.delete(session, order_id)


async def format_preorder_system(session: AsyncSession, order: models.PreOrder):
    data = order.to_dict()
    booster_dollar = order.price.booster_dollar_fee
    if booster_dollar:
        price = schemas.PreOrderPriceSystem(
            dollar=order.price.dollar,
            booster_dollar_fee=booster_dollar,
            booster_dollar=order.price.booster_dollar,
            booster_rub=await currency_flows.usd_to_currency(session, booster_dollar, order.date, "RUB", with_fee=True),
            booster_gold=order.price.booster_gold,
        )
    else:
        price = schemas.PreOrderPriceSystem(dollar=order.price.dollar)
    data["price"] = price
    data["info"] = order.info.to_dict()
    return schemas.PreOrderReadSystem.model_validate(data)


async def format_preorder_perms(session: AsyncSession, order: models.PreOrder):
    data = order.to_dict()
    booster_price = order.price.booster_dollar_fee
    if booster_price:
        price = schemas.PreOrderPriceUser(
            booster_dollar_fee=booster_price,
            booster_rub=await currency_flows.usd_to_currency(session, booster_price, order.date, "RUB"),
            booster_gold=order.price.booster_gold,
        )
    else:
        price = schemas.PreOrderPriceUser()
    data["price"] = price
    data["info"] = order.info.to_dict()
    return schemas.PreOrderReadUser.model_validate(data)


async def get_by_filter(
    session: AsyncSession,
    params: pagination.PaginationParams,
) -> pagination.Paginated[schemas.PreOrderReadUser]:
    query = (
        sa.select(models.PreOrder)
        .options(joinedload(models.PreOrder.info), joinedload(models.PreOrder.price))
        .offset(params.offset)
        .limit(params.limit)
        .order_by(params.order_by)
    )
    result = await session.execute(query)
    results = [await format_preorder_perms(session, order) for order in result.scalars()]
    total = await session.execute(sa.select(count(models.PreOrder.id)))
    return pagination.Paginated(
        page=params.page,
        per_page=params.per_page,
        total=total.one()[0],
        results=results,
    )
