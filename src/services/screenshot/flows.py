from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from src import models
from src.core import errors
from src.services.accounting import service as accounting_service

from . import service


async def create(
    session: AsyncSession,
    user: models.User,
    order: models.Order,
    url: str,
) -> models.Screenshot:
    if not user.is_superuser:
        user_order = await accounting_service.get_by_order_id_user_id(session, order.id, user.id)
        if not user_order:
            raise errors.ApiHTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=[
                    errors.ApiException(
                        msg=f"User does not have access to this order. [user_id={user.id}, order_id={order.id}]",
                        code="already_exist",
                    )
                ],
            )
    return await service.create(session, user, order, url)


async def delete(session: AsyncSession, user: models.User, screenshot_id: int) -> models.Screenshot:
    screenshot = await service.get(session, screenshot_id)
    if not screenshot:
        raise errors.ApiHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[
                errors.ApiException(
                    msg="A screenshot with this id does not exist.",
                    code="not_exist",
                )
            ],
        )
    if not user.is_superuser:
        order_id = screenshot.order_id
        user_order = await accounting_service.get_by_order_id_user_id(session, order_id, user.id)
        if not user_order:
            raise errors.ApiHTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=[
                    errors.ApiException(
                        msg=f"User does not have access to this order. [user_id={user.id}, order_id={order_id}]",
                        code="not_access",
                    )
                ],
            )
    return await service.delete(session, user, screenshot)
