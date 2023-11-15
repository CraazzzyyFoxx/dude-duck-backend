from fastapi import APIRouter, Depends

from src.core import enums, db
from src.services.auth import flows as auth_flows
from src.services.order import flows as orders_flows
from src.services.preorder import flows as preorders_flows

from . import flows, models

router = APIRouter(prefix="/message", tags=[enums.RouteTag.MESSAGES])


@router.post("", response_model=models.OrderResponse)
async def create_order_messages(
        order_id: int,
        data: models.OrderPullCreate,
        session=Depends(db.get_async_session),
        _=Depends(auth_flows.current_active_superuser)
):
    if not data.preorder:
        order = await orders_flows.format_order_system(session, await orders_flows.get(session, order_id))
        return await flows.create_order_message(order, data.categories, data.config_names, data.is_gold)
    else:
        order = await preorders_flows.format_preorder_system(session, await preorders_flows.get(session, order_id))
        return await flows.create_preorder_message(order, data.categories, data.config_names, data.is_gold)


@router.delete("", response_model=models.OrderResponse)
async def delete_order_messages(
        order_id: int,
        session=Depends(db.get_async_session),
        _=Depends(auth_flows.current_active_superuser)
):
    order = await orders_flows.format_order_system(session, await orders_flows.get(session, order_id))
    return await flows.delete_order_message(order)


@router.patch("", response_model=models.OrderResponse)
async def update_order_message(
        order_id: int,
        data: models.OrderPullUpdate,
        session=Depends(db.get_async_session),
        _=Depends(auth_flows.current_active_superuser)
):
    if not data.preorder:
        order = await orders_flows.format_order_system(session, await orders_flows.get(session, order_id))
        return await flows.update_order_message(order, data.config_names, data.is_gold)
    else:
        order = await preorders_flows.format_preorder_system(session, await preorders_flows.get(session, order_id))
        return await flows.update_preorder_message(order, data.config_names, data.is_gold)


@router.post("/sheets", response_model=models.OrderResponse)
async def create_sheets_order_messages(
        order_id: str,
        data: models.OrderPullCreate,
        session=Depends(db.get_async_session),
        _=Depends(auth_flows.current_active_superuser_api)
):
    if not data.preorder:
        order = await orders_flows.format_order_system(session, await orders_flows.get_by_order_id(session, order_id))
        return await flows.create_order_message(order, data.categories, data.config_names, data.is_gold)
    else:
        order = await preorders_flows.format_preorder_system(
            session, await preorders_flows.get_by_order_id(session, order_id)
        )
        return await flows.create_preorder_message(order, data.categories, data.config_names, data.is_gold)


@router.delete("/sheets", response_model=models.OrderResponse)
async def delete_sheets_order_messages(
        order_id: str,
        preorder: bool,
        session=Depends(db.get_async_session),
        _=Depends(auth_flows.current_active_superuser_api)
):
    if not preorder:
        order = await orders_flows.format_order_system(session, await orders_flows.get_by_order_id(session, order_id))
        return await flows.delete_order_message(order)
    else:
        order = await preorders_flows.format_preorder_system(
            session, await preorders_flows.get_by_order_id(session, order_id)
        )
        return await flows.delete_preorder_message(order)


@router.patch("/sheets", response_model=models.OrderResponse)
async def update_sheets_order_message(
        order_id: str,
        data: models.OrderPullUpdate,
        session=Depends(db.get_async_session),
        _=Depends(auth_flows.current_active_superuser_api)
):
    if not data.preorder:
        order = await orders_flows.format_order_system(session, await orders_flows.get_by_order_id(session, order_id))
        return await flows.update_order_message(order, data.config_names, data.is_gold)
    else:
        order = await preorders_flows.format_preorder_system(
            session, await preorders_flows.get_by_order_id(session, order_id))
        return await flows.update_preorder_message(order, data.config_names, data.is_gold)
