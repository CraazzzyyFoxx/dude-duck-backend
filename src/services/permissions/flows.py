from starlette import status

from src.core import errors
from src.services.auth import models as auth_models
from src.services.orders import models as order_models

from . import service


async def has_access_to_order(order: order_models.Order, user: auth_models.User):
    access = await service.has_access_to_order(order, user)
    if access:
        return True
    raise errors.DDHTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=[errors.DDException(msg="You do bot have access to this order", code="forbidden")],
    )


async def can_user_pick(user: auth_models.User) -> bool:
    if user.is_verified:
        return True

    raise errors.DDHTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=[errors.DDException(msg="Only verified users can fulfill orders", code="not_verified")],
    )
