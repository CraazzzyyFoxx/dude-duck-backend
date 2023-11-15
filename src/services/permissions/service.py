from src.services.accounting import service as accounting_service
from src.services.auth import models as auth_models
from src.services.order import models as order_models


async def has_access_to_order(order: order_models.Order, user: auth_models.User):
    access = await accounting_service.get_by_order_id_user_id(order.id, user.id)
    if access:
        return True
    return False


async def can_user_pick(user: auth_models.User) -> bool:
    if not user.is_verified:
        return False
    return True
