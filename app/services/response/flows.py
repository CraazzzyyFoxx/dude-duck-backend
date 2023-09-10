from beanie import PydanticObjectId
from fastapi import HTTPException

from starlette import status

from app.services.auth import service as auth_service
from app.services.accounting import flows as accounting_flows
from app.services.telegram.message import service as messages_service
from app.services.orders import models as order_models
from app.services.permissions import service as permissions_service
from app.services.preorders import models as preorder_models

from . import models, service


async def order_available(
        order: order_models.Order
) -> bool:
    if order.status != order_models.OrderStatus.InProgress:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=[{"msg": "You cannot respond to a completed order."}])
    responses = await service.get_by_order_id(order.id)
    for response in responses:
        if response.approved:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail=[{"msg": "Someone has already taken the order or it has been deleted."}])
    return True


async def is_already_respond(
        order: order_models.Order,
        user: auth_service.models.User
):
    response = await service.get_by_order_id_user_id(order.id, user.id)
    if response is not None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail=[{"msg": "It is impossible to respond to the same order twice."}],
                            )
    return False


async def create_response(
        user: auth_service.models.User,
        order: order_models.Order,
        response: models.ResponseExtra
):
    await order_available(order)
    await is_already_respond(order, user)
    await accounting_flows.can_user_pick_order(user, order)
    resp = await service.create(models.ResponseCreate(extra=response, order_id=order.id, user_id=user.id))
    messages_service.send_response_admin(await permissions_service.format_order(order), user, resp)
    return resp


async def create_preorder_response(
        user: auth_service.models.User,
        order: preorder_models.PreOrder,
        response: models.ResponseExtra
):
    await is_already_respond(order, user)
    resp = await service.create(models.ResponseCreate(extra=response, order_id=order.id, user_id=user.id))
    messages_service.send_preorder_response_admin(await permissions_service.format_preorder(order), user, resp)
    return resp


async def approve_response(
        user: auth_service.models.User,
        order: order_models.Order
):
    await order_available(order)
    await accounting_flows.can_user_pick_order(user, order)
    await accounting_flows.add_booster(order, user)
    await messages_service.pull_order_delete(await permissions_service.format_order(order))

    responds = await service.get_by_order_id(order_id=order.id)
    for resp in responds:
        if resp.user_id == user.id:
            await service.update(resp, models.ResponseUpdate(approved=True, closed=True))
            messages_service.send_response_approve(user, await permissions_service.format_order(order), resp)
        else:
            await service.update(resp, models.ResponseUpdate(approved=False, closed=True))
            messages_service.send_response_decline(user, await permissions_service.format_order(order))

    messages_service.send_response_chose_notify(await permissions_service.format_order(order), user, len(responds))
    return await service.get_by_order_id_user_id(order.id, user.id)


async def approve_preorder_response(
        user: auth_service.models.User,
        order: preorder_models.PreOrder
):
    await order_available(order)

    await messages_service.pull_preorder_delete(await permissions_service.format_preorder(order))

    responds = await service.get_by_order_id(order_id=order.id)
    for resp in responds:
        if resp.user_id == user.id:
            await service.update(resp, models.ResponseUpdate(approved=True, closed=True))
        else:
            await service.update(resp, models.ResponseUpdate(approved=False, closed=True))

    return await service.get_by_order_id_user_id(order.id, user.id)


async def get_by_order_id_user_id(
        order_id: PydanticObjectId,
        user_id: PydanticObjectId
) -> models.Response:
    resp = await service.get_by_order_id_user_id(order_id, user_id)
    if not resp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[{"msg": "A response with this order_id and user_id does not exist."}],
        )
    return resp


async def get(
        response_id: PydanticObjectId
) -> models.Response:
    resp = await service.get(response_id)
    if not resp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[{"msg": "A response with this id does not exist."}],
        )
    return resp


async def delete(
        response_id: PydanticObjectId
):
    response = await get(response_id)
    return await service.delete(response.id)
