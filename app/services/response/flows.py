from beanie import PydanticObjectId
from fastapi import HTTPException

from starlette import status

from app.services.auth import service as auth_service
from app.services.accounting import flows as accounting_flows
from app.services.telegram.message import service as messages_service
from app.services.orders import service as order_service

from . import models, service


async def order_available(order: order_service.models.Order) -> bool:
    if order.status != "In Progress":
        return False
    responses = await service.get_by_order_id(order.id)
    for response in responses:
        if response.approved:
            return False
    return True


async def is_already_respond(order: models.Order, user: auth_service.models.User):
    response = await service.get_by_order_id_user_id(order.id, user.id)
    if response is not None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail=[{"msg": "It is impossible to respond to the same order twice."}],
                            )
    return False


async def create_response(user: auth_service.models.User, order: models.Order, response: models.ResponseExtra):
    if not await order_available(order):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=[{"msg": "Someone has already taken the order or it has been deleted."}],
                            )
    await is_already_respond(order, user)
    await accounting_flows.can_user_pick_order(user, order)
    resp = await service.create(models.ResponseCreate(extra=response, order_id=order.id, user_id=user.id))
    resp = await service.get(resp.id)
    await messages_service.send_response_admin(order, user, resp)
    return resp


async def approve_response(user: auth_service.models.User, order: models.Order):
    if not await order_available(order):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=[{"msg": "Someone has already taken the order or it has been deleted."}])
    await accounting_flows.can_user_pick_order(user, order)

    responds = await service.get_by_order_id(order_id=order.id)
    for resp in responds:
        if resp.user.id == user.id:
            await service.update(resp, models.ResponseUpdate(approved=True, closed=True))
            await messages_service.send_response_approve(user, order, resp)
        else:
            await service.update(resp, models.ResponseUpdate(closed=True, approved=False))
            await messages_service.send_response_decline(user, order)

    await accounting_flows.add_booster(order, user)
    await messages_service.pull_delete(order)
    await messages_service.send_response_chose_notify(order, user, len(responds))
    return await service.get_by_order_id_user_id(order.id, user.id)


async def get_by_order_id_user_id(order_id: PydanticObjectId, user_id: PydanticObjectId) -> models.Response:
    resp = await service.get_by_order_id_user_id(order_id, user_id)
    if not resp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[{"msg": "A response with this order_id and user_id does not exist."}],
        )
    return resp


async def get(response_id: PydanticObjectId) -> models.Response:
    resp = await service.get(response_id)
    if not resp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[{"msg": "A response with this id does not exist."}],
        )
    return resp
