import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from starlette import status

from src.core import errors, pagination
from src.services.accounting import flows as accounting_flows
from src.services.auth import models as auth_models
from src.services.order import flows as order_flows
from src.services.order import models as order_models
from src.services.preorder import flows as preorder_flows
from src.services.preorder import models as preorder_models
from src.services.preorder import service as preorder_service
from src.services.telegram.message import service as messages_service

from . import models, service


async def get_by_order_id_user_id(
    session: AsyncSession, order_id: int, user_id: int, pre: bool = False
) -> models.Response:
    resp = await service.get_by_order_id_user_id(session, order_id, user_id, pre=pre)
    if not resp:
        raise errors.ApiHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[
                errors.ApiException(
                    msg="A response with this order_id and user_id does not exist.",
                    code="not_exist",
                )
            ],
        )
    return resp


async def get(session: AsyncSession, response_id: int, pre: bool = False) -> models.Response:
    resp = await service.get(session, response_id, pre=pre)
    if not resp:
        raise errors.ApiHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[errors.ApiException(msg="A response with this id does not exist.", code="not_exist")],
        )
    return resp


async def delete(session: AsyncSession, response_id: int, pre: bool = False) -> None:
    response = await get(session, response_id, pre=pre)
    if response:
        await service.delete(session, response_id)


async def order_available(session: AsyncSession, order: order_models.Order) -> bool:
    if order.status != order_models.OrderStatus.InProgress:
        raise errors.ApiHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[errors.ApiException(msg="You cannot respond to a completed order.", code="bad_request")],
        )
    responses = await service.get_by_order_id(session, order.id)
    for response in responses:
        if response.approved:
            raise errors.ApiHTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=[
                    errors.ApiException(
                        msg="Someone has already taken the order or it has been deleted.",
                        code="bad_request",
                    )
                ],
            )
    return True


async def is_already_respond(session: AsyncSession, order_id: int, user: auth_models.User) -> bool:
    response = await service.get_by_order_id_user_id(session, order_id, user.id)
    if response is not None:
        raise errors.ApiHTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=[
                errors.ApiException(
                    msg="It is impossible to respond to the same order twice.",
                    code="already_exist",
                )
            ],
        )
    return False


async def create_order_response(
    session: AsyncSession, user: auth_models.User, order: order_models.Order, response: models.ResponseExtra
) -> models.Response:
    await order_available(session, order)
    await is_already_respond(session, order.id, user)
    await accounting_flows.can_user_pick_order(session, user, order)
    resp = await service.create(
        session, models.ResponseCreate(order_id=order.id, user_id=user.id, **response.model_dump())
    )
    messages_service.send_order_response_admin(
        await order_flows.format_order_system(session, order),
        auth_models.UserRead.model_validate(user, from_attributes=True),
        models.ResponseRead.model_validate(resp),
    )
    return resp


async def create_preorder_response(
    session: AsyncSession, user: auth_models.User, order: preorder_models.PreOrder, response: models.ResponseExtra
) -> models.Response:
    await is_already_respond(session, order.id, user)
    resp = await service.create(
        session, models.ResponseCreate(order_id=order.id, user_id=user.id, **response.model_dump()), pre=True
    )
    messages_service.send_preorder_response_admin(
        await preorder_flows.format_preorder_system(session, order),
        auth_models.UserRead.model_validate(user, from_attributes=True),
        models.ResponseRead.model_validate(resp),
    )
    return resp


async def approve_response(session: AsyncSession, user: auth_models.User, order: order_models.Order) -> models.Response:
    await order_available(session, order)
    await accounting_flows.can_user_pick_order(session, user, order)
    await accounting_flows.add_booster(session, order, user)
    responds = await service.get_by_order_id(session, order.id)
    user_read = auth_models.UserRead.model_validate(user, from_attributes=True)
    for resp in responds:
        if not resp.closed:
            if resp.user_id == user.id:
                await service.patch(session, resp, models.ResponseUpdate(approved=True, closed=True))
                messages_service.send_response_approve(user_read, order.id, models.ResponseRead.model_validate(resp))
            else:
                await _decline_response(session, resp, order)
    await messages_service.order_delete(await order_flows.format_order_system(session, order))
    messages_service.send_response_chose_notify(order.order_id, user_read, len(responds))
    return await get_by_order_id_user_id(session, order.id, user.id)


async def _decline_response(session: AsyncSession, response: models.Response, order: order_models.Order) -> None:
    user_declined = auth_models.UserRead.model_validate(response.user, from_attributes=True)
    await service.patch(session, response, models.ResponseUpdate(approved=False, closed=True))
    messages_service.send_response_decline(user_declined, order.order_id)


async def decline_response(session: AsyncSession, user: auth_models.User, order: order_models.Order) -> models.Response:
    responds = await service.get_by_order_id(session, order.id)
    for resp in responds:
        if resp.user_id == user.id:
            await _decline_response(session, resp, order)
    return await get_by_order_id_user_id(session, order.id, user.id)


async def approve_preorder_response(
    session: AsyncSession, user: auth_models.User, order: preorder_models.PreOrder
) -> models.Response:
    await messages_service.order_delete(await preorder_flows.format_preorder_system(session, order), pre=True)
    for resp in await service.get_by_order_id(session, order_id=order.id):
        await service.patch(session, resp, models.ResponseUpdate(approved=resp.user_id == user.id, closed=True))
    await preorder_service.update(session, order, preorder_models.PreOrderUpdate(has_response=True))
    return await get_by_order_id_user_id(session, order.id, user.id, pre=True)


async def _decline_preorder_response(
    session: AsyncSession, response: models.Response, order: preorder_models.PreOrder
) -> None:
    user_declined = auth_models.UserRead.model_validate(response.user, from_attributes=True)
    await service.patch(session, response, models.ResponseUpdate(approved=False, closed=True))
    messages_service.send_response_decline(user_declined, order.order_id)


async def decline_preorder_response(
    session: AsyncSession, user: auth_models.User, order: preorder_models.PreOrder
) -> models.Response:
    responds = await service.get_by_order_id(session, order.id)
    for resp in responds:
        if resp.user_id == user.id:
            await _decline_preorder_response(session, resp, order)
    return await get_by_order_id_user_id(session, order.id, user.id, pre=True)


async def get_by_filter(
    session: AsyncSession, params: models.ResponsePagination
) -> pagination.Paginated[models.ResponseRead]:
    if params.order_id:
        _ = await order_flows.get(session, params.order_id)
    query = sa.select(models.Response).options(joinedload(models.Response.user))
    query = params.apply_filter(query)
    query = params.apply_pagination(query)
    result = await session.execute(query)
    results = [models.ResponseRead.model_validate(resp, from_attributes=True) for resp in result.scalars().all()]
    total = await session.execute(params.apply_filter(sa.select(sa.func.count(models.Response.id))))
    return pagination.Paginated(results=results, total=total.scalar_one(), page=params.page, per_page=params.per_page)
