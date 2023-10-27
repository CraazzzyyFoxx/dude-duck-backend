from fastapi import APIRouter, Depends

from src.core import enums, db
from src.services.auth import flows as auth_flows
from src.services.orders import flows as orders_flows
from src.services.preorders import flows as preorders_flows

from . import flows, models

router = APIRouter(prefix="/messages", tags=[enums.RouteTag.MESSAGES])
router_api = APIRouter(dependencies=[Depends(auth_flows.current_active_superuser_api)])
router_user = APIRouter(dependencies=[Depends(auth_flows.current_active_superuser)])


@router_user.post("/{order_id}", response_model=models.OrderResponse)
async def create_order_messages(order_id: int, data: models.OrderPullCreate, session=Depends(db.get_async_session)):
    if not data.preorder:
        order = await orders_flows.format_order_system(session, await orders_flows.get(session, order_id))
        return await flows.create_order_message(order, data.categories, data.config_names, data.is_gold)
    else:
        order = await preorders_flows.format_preorder_system(session, await preorders_flows.get(session, order_id))
        return await flows.create_preorder_message(order, data.categories, data.config_names, data.is_gold)


@router_user.delete("/{order_id}", response_model=models.OrderResponse)
async def delete_order_messages(order_id: int, session=Depends(db.get_async_session)):
    order = await orders_flows.format_order_system(session, await orders_flows.get(session, order_id))
    return await flows.delete_order_message(order)


@router_user.patch("/{order_id}", response_model=models.OrderResponse)
async def update_order_message(order_id: int, data: models.OrderPullUpdate, session=Depends(db.get_async_session)):
    if not data.preorder:
        order = await orders_flows.format_order_system(session, await orders_flows.get(session, order_id))
        return await flows.update_order_message(order, data.config_names, data.is_gold)
    else:
        order = await preorders_flows.format_preorder_system(session, await preorders_flows.get(session, order_id))
        return await flows.update_preorder_message(order, data.config_names, data.is_gold)


@router_api.post("/sheets/{order_id}", response_model=models.OrderResponse)
async def create_sheets_order_messages(
        order_id: str, data: models.OrderPullCreate, session=Depends(db.get_async_session)
):
    if not data.preorder:
        order = await orders_flows.format_order_system(session, await orders_flows.get_by_order_id(session, order_id))
        return await flows.create_order_message(order, data.categories, data.config_names, data.is_gold)
    else:
        order = await preorders_flows.format_preorder_system(
            session, await preorders_flows.get_by_order_id(session, order_id)
        )
        return await flows.create_preorder_message(order, data.categories, data.config_names, data.is_gold)


@router_api.delete("/sheets/{order_id}", response_model=models.OrderResponse)
async def delete_sheets_order_messages(order_id: str, preorder: bool, session=Depends(db.get_async_session)):
    if not preorder:
        order = await orders_flows.format_order_system(session, await orders_flows.get_by_order_id(session, order_id))
        return await flows.delete_order_message(order)
    else:
        order = await preorders_flows.format_preorder_system(
            session, await preorders_flows.get_by_order_id(session, order_id)
        )
        return await flows.delete_preorder_message(order)


@router_api.patch("/sheets/{order_id}", response_model=models.OrderResponse)
async def update_sheets_order_message(
        order_id: str, data: models.OrderPullUpdate, session=Depends(db.get_async_session)
):
    if not data.preorder:
        order = await orders_flows.format_order_system(session, await orders_flows.get_by_order_id(session, order_id))
        return await flows.update_order_message(order, data.config_names, data.is_gold)
    else:
        order = await preorders_flows.format_preorder_system(
            session, await preorders_flows.get_by_order_id(session, order_id))
        return await flows.update_preorder_message(order, data.config_names, data.is_gold)


router.include_router(router_api)
router.include_router(router_user)
