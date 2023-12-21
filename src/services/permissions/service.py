from sqlalchemy.ext.asyncio import AsyncSession

from src import models
from src.services.accounting import service as accounting_service


async def has_access_to_order(session: AsyncSession, order: models.Order, user: models.User):
    access = await accounting_service.get_by_order_id_user_id(session, order.id, user.id)
    if access:
        return True
    return False


async def can_user_pick(user: models.User) -> bool:
    if not user.is_verified:
        return False
    return True
