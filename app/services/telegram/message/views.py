from beanie import PydanticObjectId
from fastapi import APIRouter, Depends

from app.core import enums
from app.services.auth import flows as auth_flows
from app.services.orders import flows as orders_flows
from app.services.preorders import flows as preorders_flows

from . import flows, models

router = APIRouter(prefix="/messages", tags=[enums.RouteTag.MESSAGES])
router_api = APIRouter(dependencies=[Depends(auth_flows.current_active_superuser_api)])
router_user = APIRouter(dependencies=[Depends(auth_flows.current_active_superuser)])


@router_user.post("/{order_id}", response_model=models.OrderResponse)
async def create_order_messages(order_id: PydanticObjectId, data: models.OrderPullCreate):
    if not data.preorder:
        order = await orders_flows.format_order_system(await orders_flows.get(order_id))
        return await flows.create_order_message(order, data.categories, data.config_names, data.is_gold)
    else:
        order = await preorders_flows.format_preorder_system(await preorders_flows.get(order_id))
        return await flows.create_preorder_message(order, data.categories, data.config_names, data.is_gold)


@router_user.delete("/{order_id}", response_model=models.OrderResponse)
async def delete_order_messages(order_id: PydanticObjectId):
    order = await orders_flows.format_order_system(await orders_flows.get(order_id))
    return await flows.delete_order_message(order)


@router_user.patch("/{order_id}", response_model=models.OrderResponse)
async def update_order_message(order_id: PydanticObjectId, data: models.OrderPullUpdate):
    if not data.preorder:
        order = await orders_flows.format_order_system(await orders_flows.get(order_id))
        return await flows.update_order_message(order, data.config_names, data.is_gold)
    else:
        order = await preorders_flows.format_preorder_system(await preorders_flows.get(order_id))
        return await flows.update_preorder_message(order, data.config_names, data.is_gold)


@router_api.post("/sheets/{order_id}", response_model=models.OrderResponse)
async def create_sheets_order_messages(order_id: str, data: models.OrderPullCreate):
    if not data.preorder:
        order = await orders_flows.format_order_system(await orders_flows.get_by_order_id(order_id))
        return await flows.create_order_message(order, data.categories, data.config_names, data.is_gold)
    else:
        order = await preorders_flows.format_preorder_system(await preorders_flows.get_order_id(order_id))
        return await flows.create_preorder_message(order, data.categories, data.config_names, data.is_gold)


@router_api.delete("/sheets/{order_id}", response_model=models.OrderResponse)
async def delete_sheets_order_messages(order_id: str):
    order = await orders_flows.format_order_system(await orders_flows.get_by_order_id(order_id))
    return await flows.delete_order_message(order)


@router_api.patch("/sheets/{order_id}", response_model=models.OrderResponse)
async def update_sheets_order_message(order_id: str, data: models.OrderPullUpdate):
    if not data.preorder:
        order = await orders_flows.format_order_system(await orders_flows.get_by_order_id(order_id))
        return await flows.update_order_message(order, data.config_names, data.is_gold)
    else:
        order = await preorders_flows.format_preorder_system(await preorders_flows.get_order_id(order_id))
        return await flows.update_preorder_message(order, data.config_names, data.is_gold)


router.include_router(router_api)
router.include_router(router_user)
