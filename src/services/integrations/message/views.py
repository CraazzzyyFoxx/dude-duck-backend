import sqlalchemy as sa
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src import models, schemas
from src.core import db, enums, pagination
from src.services.auth import flows as auth_flows
from src.services.integrations.notifications import flows as notifications_flows
from src.services.order import flows as order_flows
from src.services.preorder import flows as preorder_flows

from . import service

router = APIRouter(
    prefix="/integrations/message",
    tags=[enums.RouteTag.MESSAGES],
    dependencies=[Depends(auth_flows.current_active_superuser)],
)


@router.get("/order/filter", response_model=pagination.Paginated[schemas.OrderMessageRead])
async def read_order_messages(
    params: schemas.OrderMessagePaginationParams = Depends(),
    session=Depends(db.get_async_session),
):
    return await service.get_order_messages_by_filter(session, params)


@router.post("/order", response_model=schemas.MessageCallback)
async def create_order_message(data: schemas.CreateOrderMessage, session=Depends(db.get_async_session)):
    if data.is_preorder:
        preorder = await preorder_flows.get(session, data.order_id)
        preorder_read = await preorder_flows.format_preorder_system(session, preorder)
        resp = await service.create_order_message(session, preorder_read, data)
        notifications_flows.send_sent_order_notify(preorder.order_id, data.integration, resp)
    else:
        order = await order_flows.get(session, data.order_id)
        order_read = await order_flows.format_order_system(session, order)
        resp = await service.create_order_message(session, order_read, data)
        notifications_flows.send_sent_order_notify(order.order_id, data.integration, resp)
    return resp


@router.delete("/order", response_model=schemas.MessageCallback)
async def delete_order_message(data: schemas.DeleteOrderMessage, session=Depends(db.get_async_session)):
    if data.is_preorder:
        preorder = await preorder_flows.get(session, data.order_id)
        resp = await service.delete_order_message(session, data)
        notifications_flows.send_deleted_order_notify(preorder.order_id, data.integration, resp)
    else:
        order = await order_flows.get(session, data.order_id)
        resp = await service.delete_order_message(session, data)
        notifications_flows.send_deleted_order_notify(order.order_id, data.integration, resp)
    return resp


@router.patch("/order", response_model=schemas.MessageCallback)
async def update_order_message(data: schemas.UpdateOrderMessage, session=Depends(db.get_async_session)):
    if data.is_preorder:
        preorder = await preorder_flows.get(session, data.order_id)
        preorder_read = await preorder_flows.format_preorder_system(session, preorder)
        resp = await service.update_order_message(session, preorder_read, data)
        notifications_flows.send_edited_order_notify(preorder.order_id, data.integration, resp)
    else:
        order = await order_flows.get(session, data.order_id)
        order_read = await order_flows.format_order_system(session, order)
        resp = await service.update_order_message(session, order_read, data)
        notifications_flows.send_edited_order_notify(order.order_id, data.integration, resp)
    return resp


@router.get("/user/filter", response_model=pagination.Paginated[schemas.UserMessageRead])
async def read_user_messages(
    params: schemas.UserMessagePaginationParams = Depends(),
    session=Depends(db.get_async_session),
):
    return await service.get_user_messages_by_filter(session, params)


@router.post("/user", response_model=schemas.MessageCallback)
async def create_user_message(data: schemas.CreateUserMessage, session: AsyncSession = Depends(db.get_async_session)):
    if data.user_id == "@everyone":
        query = sa.select(models.UserNotification).where(models.UserNotification.type == data.integration)

        users = await session.scalars(query)
        for user in users:
            await service.create_user_message(
                session, schemas.CreateUserMessage(user_id=user.user_id, integration=data.integration, text=data.text)
            )
    else:
        return await service.create_user_message(session, data)


@router.delete("/user", response_model=schemas.MessageCallback)
async def delete_user_message(data: schemas.DeleteUserMessage, session=Depends(db.get_async_session)):
    return await service.delete_user_message(session, data)


@router.patch("/user", response_model=schemas.MessageCallback)
async def update_user_message(data: schemas.UpdateUserMessage, session=Depends(db.get_async_session)):
    return await service.update_user_message(session, data)


@router.get("/response/filter", response_model=pagination.Paginated[schemas.ResponseMessageRead])
async def read_response_messages(
    params: schemas.ResponseMessagePaginationParams = Depends(),
    session=Depends(db.get_async_session),
):
    return await service.get_response_messages_by_filter(session, params)
