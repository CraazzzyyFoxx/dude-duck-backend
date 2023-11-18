from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from src.core import errors
from src.services.auth import models as auth_models
from src.services.order import models as order_models

from . import service


async def has_access_to_order(session: AsyncSession, order: order_models.Order, user: auth_models.User):
    access = await service.has_access_to_order(session, order, user)
    if access:
        return True
    raise errors.ApiHTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=[errors.ApiException(msg="You do bot have access to this order", code="forbidden")],
    )


async def can_user_pick(user: auth_models.User) -> bool:
    if user.is_verified:
        return True

    raise errors.ApiHTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=[errors.ApiException(msg="Only verified users can fulfill orders", code="not_verified")],
    )
