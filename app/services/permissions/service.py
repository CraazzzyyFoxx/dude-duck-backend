from loguru import logger

from app.services.orders import service as order_service
from app.services.auth import service as auth_service
from app.services.accounting import service as accounting_service


async def have_access_to_order(order: order_service.models.Order, user: auth_service.models.User) -> bool:
    return True


async def format_order(order: order_service.models.Order, user: auth_service.models.User):
    data = dict(order)
    if user.is_superuser:
        price = order_service.schemas.OrderPrice(
            price_booster_dollar_fee=accounting_service.calculate_price_dollars(order.price.price_booster_dollar_fee),
            price_booster_rub=accounting_service.calculate_price_rub(order.price.price_booster_dollar_fee,
                                                                     order.exchange),
            price_dollar=accounting_service.calculate_price_dollars(order.price.price_dollar),
            price_booster_dollar=accounting_service.calculate_price_dollars(order.price.price_booster_dollar)
        )
        data["price"] = price
        return order_service.schemas.OrderRead.model_validate(data)
    else:
        price = order_service.schemas.OrderPriceUser(
            price_booster_dollar_fee=accounting_service.calculate_price_dollars(order.price.price_booster_dollar_fee),
            price_booster_rub=accounting_service.calculate_price_rub(order.price.price_booster_dollar_fee,
                                                                     order.exchange))
        data["price"] = price
        return order_service.schemas.OrderReadUser(**dict(order))


async def format_order_active(
        order: order_service.models.Order,
        user: auth_service.models.User,
        order_user: accounting_service.models.UserOrder
):
    if user.is_superuser:
        price = order_service.schemas.OrderPrice(
            price_booster_dollar_fee=accounting_service.calculate_price_dollars(order_user.dollars),
            price_booster_rub=accounting_service.calculate_price_rub(order_user.dollars, order.exchange),
            price_dollar=accounting_service.calculate_price_dollars(order.price.price_dollar),
            price_booster_dollar=accounting_service.calculate_price_dollars(order.price.price_booster_dollar)
        )
        data = dict(order)
        data["price"] = price
        return order_service.schemas.OrderRead(**data)
    else:
        price = order_service.schemas.OrderPriceUser(
            price_booster_dollar_fee=accounting_service.calculate_price_dollars(order_user.dollars),
            price_booster_rub=accounting_service.calculate_price_rub(order_user.dollars, order.exchange)
        )
        data = dict(order)
        data["price"] = price
        if user.id == order_user.user.id:
            data["credentials"] = order.credentials
        return order_service.schemas.OrderReadUser(**data)
