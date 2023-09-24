from beanie import PydanticObjectId
from starlette import status

from app.core import errors
from app.services.accounting import flows as accounting_flows
from app.services.auth import models as auth_models
from app.services.auth import service as auth_service
from app.services.orders import flows as order_flows
from app.services.orders import models as order_models
from app.services.preorders import flows as preorder_flows
from app.services.preorders import models as preorder_models
from app.services.preorders import service as preorder_service
from app.services.telegram.message import service as messages_service

from . import models, service


async def get_by_order_id_user_id(order_id: PydanticObjectId, user_id: PydanticObjectId) -> models.Response:
    resp = await service.get_by_order_id_user_id(order_id, user_id)
    if not resp:
        raise errors.DudeDuckHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[
                errors.DudeDuckException(
                    msg="A response with this order_id and user_id does not exist.",
                    code="not_exist",
                )
            ],
        )
    return resp


async def get(response_id: PydanticObjectId) -> models.Response:
    resp = await service.get(response_id)
    if not resp:
        raise errors.DudeDuckHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[errors.DudeDuckException(msg="A response with this id does not exist.", code="not_exist")],
        )
    return resp


async def delete(response_id: PydanticObjectId) -> None:
    response = await get(response_id)
    return await service.delete(response.id)


async def order_available(order: order_models.Order) -> bool:
    if order.status != order_models.OrderStatus.InProgress:
        raise errors.DudeDuckHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[errors.DudeDuckException(msg="You cannot respond to a completed order.", code="cannot_response")],
        )
    responses = await service.get_by_order_id(order.id)
    for response in responses:
        if response.approved:
            raise errors.DudeDuckHTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=[
                    errors.DudeDuckException(
                        msg="Someone has already taken the order or it has been deleted.",
                        code="cannot_response",
                    )
                ],
            )
    return True


async def is_already_respond(order_id: PydanticObjectId, user: auth_models.User) -> bool:
    response = await service.get_by_order_id_user_id(order_id, user.id)
    if response is not None:
        raise errors.DudeDuckHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[
                errors.DudeDuckException(
                    msg="It is impossible to respond to the same order twice.",
                    code="already_respond",
                )
            ],
        )
    return False


async def create_response(
    user: auth_models.User, order: order_models.Order, response: models.ResponseExtra
) -> models.Response:
    await order_available(order)
    await is_already_respond(order.id, user)
    await accounting_flows.can_user_pick_order(user, order)
    resp = await service.create(models.ResponseCreate(extra=response, order_id=order.id, user_id=user.id))
    messages_service.send_response_admin(
        await order_flows.format_order_system(order),
        auth_models.UserRead.model_validate(user, from_attributes=True),
        models.ResponseRead.model_validate(resp),
    )
    return resp


async def create_preorder_response(
    user: auth_models.User, order: preorder_models.PreOrder, response: models.ResponseExtra
) -> models.Response:
    await is_already_respond(order.id, user)
    resp = await service.create(models.ResponseCreate(extra=response, order_id=order.id, user_id=user.id))
    messages_service.send_preorder_response_admin(
        await preorder_flows.format_preorder_system(order),
        auth_models.UserRead.model_validate(user, from_attributes=True),
        models.ResponseRead.model_validate(resp),
    )
    return resp


async def approve_response(user: auth_models.User, order: order_models.Order) -> models.Response:
    await order_available(order)
    await accounting_flows.can_user_pick_order(user, order)
    await accounting_flows.add_booster(order, user)
    responds = await service.get_by_order_id(order.id)
    user_approved = auth_models.UserRead.model_validate(user, from_attributes=True)
    for resp in responds:
        if resp.user_id == user.id:
            await service.update(resp, models.ResponseUpdate(approved=True, closed=True))
            messages_service.send_response_approve(user_approved, order.id, models.ResponseRead.model_validate(resp))
        else:
            await service.update(resp, models.ResponseUpdate(approved=False, closed=True))
            user_declined = await auth_service.get(resp.user_id)
            user_declined_read = auth_models.UserRead.model_validate(user_declined, from_attributes=True)
            messages_service.send_response_decline(user_declined_read, order.order_id)
    await messages_service.pull_order_delete(await order_flows.format_order_system(order))
    messages_service.send_response_chose_notify(order.order_id, user_approved, len(responds))
    return await get_by_order_id_user_id(order.id, user.id)


async def approve_preorder_response(user: auth_models.User, order: preorder_models.PreOrder) -> models.Response:
    await messages_service.pull_order_delete(await preorder_flows.format_preorder_system(order), pre=True)
    for resp in await service.get_by_order_id(order_id=order.id):
        await service.update(resp, models.ResponseUpdate(approved=resp.user_id == user.id, closed=True))
    await preorder_service.update(order, preorder_models.PreOrderUpdate(has_response=True))
    return await get_by_order_id_user_id(order.id, user.id)
