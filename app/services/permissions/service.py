from app.services.orders import models as order_models
from app.services.orders import schemas as order_schemas
from app.services.preorders import models as preorder_models
from app.services.auth import service as auth_service
from app.services.accounting import service as accounting_service


async def format_order(order: order_models.Order, _: auth_service.models.User = None):
    data = dict(order)
    price = order_schemas.OrderPriceUser(
        price_booster_dollar_fee=await accounting_service.usd_to_currency(
            order.price.price_booster_dollar, order.date, with_fee=True
        ),
        price_booster_rub=await accounting_service.usd_to_currency(
            order.price.price_booster_dollar, order.date, "RUB", with_fee=True
        )
    )
    data["price"] = price
    return order_schemas.OrderReadUser(**data)


async def format_preorder(order: preorder_models.PreOrder, _: auth_service.models.User = None):
    data = dict(order)
    if order.price.price_dollar is not None:
        price = preorder_models.PreOrderPriceUser(
            price_booster_dollar_fee=await accounting_service.usd_to_currency(
                order.price.price_booster_dollar, order.date, with_fee=True
            ),
            price_booster_rub=await accounting_service.usd_to_currency(
                order.price.price_booster_dollar, order.date, "RUB", with_fee=True
            )
        )
    else:
        price = preorder_models.PreOrderPriceUser()
    data["price"] = price
    return preorder_models.PreOrderRead(**data)


async def format_order_active(
        order: order_models.Order,
        user: auth_service.models.User,
        order_user: accounting_service.models.UserOrder
):
    price = order_schemas.OrderPriceUser(
        price_booster_dollar_fee=await accounting_service.usd_to_currency(
            order_user.dollars, order.date, with_round=True
        ),
        price_booster_rub=await accounting_service.usd_to_currency(
            order_user.dollars, order.date, "RUB", with_round=True
        )
    )
    data = dict(order)
    data["price"] = price
    if user.id == order_user.user_id:
        data["credentials"] = order.credentials
    return order_schemas.OrderReadUser(**data)
