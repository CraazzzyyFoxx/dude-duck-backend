from beanie import PydanticObjectId
from starlette import status
from tortoise.expressions import Q

from app.core import errors
from app.services.accounting import models as accounting_models
from app.services.currency import flows as currency_flows
from app.services.search import models as search_models
from app.services.search import service as search_service

from . import models, schemas, service


async def get(order_id: PydanticObjectId) -> models.Order:
    order = await service.get(order_id)
    if not order:
        raise errors.DudeDuckHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[errors.DudeDuckException(msg="A order with this id does not exist.", code="not_exist")],
        )
    return order


async def get_by_order_id(order_id: str) -> models.Order:
    order = await service.get_order_id(order_id)
    if not order:
        raise errors.DudeDuckHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[
                errors.DudeDuckException(
                    msg=f"A order with this id does not exist. [order_id={order_id}]", code="not_exist"
                )
            ],
        )
    return order


async def create(order_in: models.OrderCreate) -> models.Order:
    order = await service.get_order_id(order_in.order_id)
    if order:
        raise errors.DudeDuckHTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=[
                errors.DudeDuckException(
                    msg=f"A order with this id already exist. [order_id={order_in.order_id}]", code="already_exist"
                )
            ],
        )
    order = await service.create(order_in)
    return order


async def format_order_system(order: models.Order):
    data = dict(order)
    booster_price = order.price.price_booster_dollar
    price = schemas.OrderPriceSystem(
        price_dollar=order.price.price_dollar,
        price_booster_dollar_without_fee=booster_price,
        price_booster_dollar=await currency_flows.usd_to_currency(booster_price, order.date, with_fee=True),
        price_booster_rub=await currency_flows.usd_to_currency(booster_price, order.date, "RUB", with_fee=True),
        price_booster_gold=order.price.price_booster_gold,
    )
    data["price"] = price
    return schemas.OrderReadSystem.model_validate(data)


async def format_order_perms(order: models.Order, *, has: bool = False):
    data = dict(order)
    booster_price = order.price.price_booster_dollar
    price = schemas.OrderPriceUser(
        price_booster_dollar=await currency_flows.usd_to_currency(booster_price, order.date, with_fee=True),
        price_booster_rub=await currency_flows.usd_to_currency(booster_price, order.date, "RUB", with_fee=True),
        price_booster_gold=order.price.price_booster_gold,
    )
    data["price"] = price
    if has:
        return schemas.OrderReadHasPerms.model_validate(data)
    return schemas.OrderReadNoPerms.model_validate(data)


async def format_order_active(order: models.Order, order_active: accounting_models.UserOrder):
    data = dict(order)
    booster_price = order_active.dollars

    price = schemas.OrderPriceUser(
        price_booster_dollar=await currency_flows.usd_to_currency(booster_price, order.date),
        price_booster_rub=await currency_flows.usd_to_currency(booster_price, order.date, "RUB"),
        price_booster_gold=order.price.price_booster_gold,
    )
    data["price"] = price
    data["paid_at"] = order_active.paid_at
    return schemas.OrderReadActive.model_validate(data)


async def get_filter(paging: search_models.PaginationParams, sorting: search_models.OrderSortingParams):
    query = []
    if sorting.completed != search_models.OrderSelection.ALL:
        if sorting.completed == search_models.OrderSelection.Completed:
            query.append(Q(completed=True))
        else:
            query.append(Q(completed=False))
    return await search_service.paginate(accounting_models.UserOrder.filter(Q(*query)), paging, sorting)
