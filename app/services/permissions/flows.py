from starlette import status

from app.core import errors
from app.services.auth import models as auth_models
from app.services.orders import models as order_models

from . import service


async def has_access_to_order(order: order_models.Order, user: auth_models.User):
    access = await service.has_access_to_order(order, user)
    if access:
        return True
    raise errors.DudeDuckHTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=[errors.DudeDuckException(msg="You do bot have access to this order", code="forbidden")]
    )


async def can_user_pick(user: auth_models.User) -> bool:
    if user.is_verified:
        return True

    raise errors.DudeDuckHTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=[errors.DudeDuckException(msg="Only verified users can fulfill orders", code="not_verified")]
    )
