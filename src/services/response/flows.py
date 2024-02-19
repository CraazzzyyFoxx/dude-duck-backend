import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from starlette import status

from src import models, schemas
from src.core import enums, errors, pagination
from src.services.accounting import flows as accounting_flows
from src.services.integrations.message import service as message_flows
from src.services.integrations.notifications import flows as notifications_flows
from src.services.integrations.render import flows as render_flows
from src.services.order import flows as order_flows
from src.services.preorder import flows as preorder_flows
from src.services.preorder import service as preorder_service

from . import service


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


async def order_available(session: AsyncSession, order: models.Order) -> bool:
    if order.status != models.OrderStatus.InProgress:
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


async def is_already_respond(session: AsyncSession, order_id: int, user: models.User) -> bool:
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
    session: AsyncSession,
    user: models.User,
    order: models.PreOrder | models.Order,
    response: schemas.ResponseExtra,
    is_preorder: bool = False,
) -> models.Response:
    await is_already_respond(session, order.id, user)
    resp = await service.create(
        session,
        schemas.ResponseCreate(order_id=order.id, user_id=user.id, **response.model_dump()),
        is_preorder=is_preorder,
    )
    await message_flows.create_response_message(
        session,
        await preorder_flows.format_preorder_system(session, order)
        if is_preorder
        else await order_flows.format_order_system(session, order),
        schemas.UserRead.model_validate(user, from_attributes=True),
        schemas.CreateResponseMessage(
            integration=enums.Integration.telegram, order_id=order.id, is_preorder=is_preorder, user_id=user.id
        ),
    )
    return resp


async def approve_response(session: AsyncSession, user: models.User, order: models.Order) -> models.Response:
    await order_available(session, order)
    await accounting_flows.can_user_pick_order(session, user, order)
    await accounting_flows.add_booster(session, order, user)
    responds = await service.get_by_order_id(session, order.id)
    user_read = schemas.UserRead.model_validate(user, from_attributes=True)
    order_read = await order_flows.format_order_system(session, order)
    for resp in responds:
        if not resp.closed:
            if resp.user_id == user.id:
                await service.update(
                    session,
                    resp,
                    schemas.ResponseUpdate(approved=True, closed=True),
                    patch=True,
                )
                text = await render_flows.get_order_text(
                    session,
                    enums.Integration.telegram,
                    render_flows.get_order_configs(order_read, creds=True),
                    data={"order": order_read},
                )
                notifications_flows.send_response_approved(
                    user_read,
                    order_read,
                    schemas.ResponseRead.model_validate(resp),
                    text,
                )
            else:
                await _decline_response(session, resp, order)
    notifications_flows.send_response_chose_notify(
        order.order_id, await notifications_flows.get_user_accounts(session, user_read), len(responds)
    )
    await message_flows.delete_order_message(
        session,
        data=schemas.DeleteOrderMessage(
            order_id=order.id,
            integration=enums.Integration.telegram,
        ),
    )
    await message_flows.delete_order_message(
        session,
        data=schemas.DeleteOrderMessage(
            order_id=order.id,
            integration=enums.Integration.discord,
        ),
    )
    return await get_by_order_id_user_id(session, order.id, user.id)


async def _decline_response(session: AsyncSession, response: models.Response, order: models.Order) -> None:
    user_declined = schemas.UserRead.model_validate(response.user, from_attributes=True)
    await service.update(
        session,
        response,
        schemas.ResponseUpdate(approved=False, closed=True),
        patch=True,
    )
    notifications_flows.send_response_declined(user_declined, order.order_id)


async def decline_response(session: AsyncSession, user: models.User, order: models.Order) -> models.Response:
    responds = await service.get_by_order_id(session, order.id)
    for resp in responds:
        if resp.user_id == user.id:
            await _decline_response(session, resp, order)
    return await get_by_order_id_user_id(session, order.id, user.id)


async def approve_preorder_response(
    session: AsyncSession, user: models.User, order: models.PreOrder
) -> models.Response:
    await message_flows.delete_order_message(
        session,
        data=schemas.DeleteOrderMessage(
            order_id=order.id,
            integration=enums.Integration.telegram,
            is_preorder=True,
        ),
    )
    await message_flows.delete_order_message(
        session,
        data=schemas.DeleteOrderMessage(
            order_id=order.id,
            integration=enums.Integration.discord,
            is_preorder=True,
        ),
    )
    for resp in await service.get_by_order_id(session, order_id=order.id):
        await service.update(
            session,
            resp,
            schemas.ResponseUpdate(approved=resp.user_id == user.id, closed=True),
            patch=True,
        )
    await preorder_service.update(session, order, schemas.PreOrderUpdate(has_response=True))
    return await get_by_order_id_user_id(session, order.id, user.id, pre=True)


async def _decline_preorder_response(session: AsyncSession, response: models.Response, order: models.PreOrder) -> None:
    user_declined = schemas.UserRead.model_validate(response.user, from_attributes=True)
    await service.update(
        session,
        response,
        schemas.ResponseUpdate(approved=False, closed=True),
        patch=True,
    )
    notifications_flows.send_response_declined(user_declined, order.order_id)


async def decline_preorder_response(
    session: AsyncSession, user: models.User, order: models.PreOrder
) -> models.Response:
    responds = await service.get_by_order_id(session, order.id)
    for resp in responds:
        if resp.user_id == user.id:
            await _decline_preorder_response(session, resp, order)
    return await get_by_order_id_user_id(session, order.id, user.id, pre=True)


async def get_by_filter(
    session: AsyncSession, params: schemas.ResponsePagination
) -> pagination.Paginated[schemas.ResponseRead]:
    if params.order_id:
        _ = await order_flows.get(session, params.order_id)
    query = sa.select(models.Response).options(joinedload(models.Response.user))
    query = params.apply_filter(query)
    query = params.apply_pagination(query)
    result = await session.execute(query)
    results = [schemas.ResponseRead.model_validate(resp, from_attributes=True) for resp in result.scalars().all()]
    total = await session.execute(params.apply_filter(sa.select(sa.func.count(models.Response.id))))
    return pagination.Paginated(
        results=results,
        total=total.scalar_one(),
        page=params.page,
        per_page=params.per_page,
    )
