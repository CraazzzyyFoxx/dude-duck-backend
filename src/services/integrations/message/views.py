from fastapi import APIRouter, Depends

from src.core import db, enums, pagination
from src.services.auth import flows as auth_flows
from src.services.order import flows as order_flows
from src.services.preorder import flows as preorder_flows

from . import flows, models

router = APIRouter(
    prefix="/integrations/message",
    tags=[enums.RouteTag.MESSAGES],
    dependencies=[Depends(auth_flows.current_active_superuser)],
)


@router.get("/filter", response_model=pagination.Paginated[models.MessageRead])
async def reads_order_message(
    params: models.MessagePaginationParams = Depends(), session=Depends(db.get_async_session)
):
    return await flows.get_by_filter(session, params)


@router.post("", response_model=models.OrderResponse)
async def create_order_message(order_id: int, data: models.OrderPullCreate, session=Depends(db.get_async_session)):
    if data.preorder:
        preorder = await preorder_flows.get(session, order_id)
        preorder_read = await preorder_flows.format_preorder_system(session, preorder)
        return await flows.pull_create(
            session, data.integration, preorder_read, data.categories, data.config_names, True, data.is_gold
        )
    else:
        order = await order_flows.get(session, order_id)
        order_read = await order_flows.format_order_system(session, order)
        return await flows.pull_create(
            session, data.integration, order_read, data.categories, data.config_names, False, data.is_gold
        )


@router.delete("", response_model=models.OrderResponse)
async def delete_order_message(order_id: int, data: models.OrderPullDelete, session=Depends(db.get_async_session)):
    if data.preorder:
        preorder = await preorder_flows.get(session, order_id)
        preorder_read = await preorder_flows.format_preorder_system(session, preorder)
        return await flows.pull_delete(session, data.integration, preorder_read, True)
    else:
        order = await order_flows.get(session, order_id)
        order_read = await order_flows.format_order_system(session, order)
        return await flows.pull_delete(session, data.integration, order_read, False)


@router.patch("", response_model=models.OrderResponse)
async def update_order_message(order_id: int, data: models.OrderPullUpdate, session=Depends(db.get_async_session)):
    if data.preorder:
        preorder = await preorder_flows.get(session, order_id)
        preorder_read = await preorder_flows.format_preorder_system(session, preorder)
        return await flows.pull_update(session, data.integration, preorder_read, data.config_names, True, data.is_gold)
    else:
        order = await order_flows.get(session, order_id)
        order_read = await order_flows.format_order_system(session, order)
        return await flows.pull_update(session, data.integration, order_read, data.config_names, False, data.is_gold)
