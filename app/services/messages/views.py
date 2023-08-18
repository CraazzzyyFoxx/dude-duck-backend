from fastapi import APIRouter, Depends
from beanie import PydanticObjectId

from app.core import enums
from app.services.auth import service as auth_service
from app.services.orders import flows as orders_flows

from . import models, flows

router = APIRouter(prefix='/messages', tags=[enums.RouteTag.MESSAGES])
router_api = APIRouter(dependencies=[Depends(auth_service.current_active_superuser_api)])
router_user = APIRouter(dependencies=[Depends(auth_service.current_active_superuser)])


@router_user.post('/{order_id}', response_model=list[models.OrderMessage])
async def create_order_messages(order_id: PydanticObjectId, data: models.OrderPullCreate):
    order = await orders_flows.get(order_id)
    return await flows.create_order_message(order, data.categories, data.config_names)


@router_user.delete('/{order_id}', response_model=list[models.OrderMessage])
async def delete_order_messages(order_id: PydanticObjectId):
    order = await orders_flows.get(order_id)
    return await flows.delete_order_message(order)


@router_user.patch('/{order_id}', response_model=list[models.OrderMessage])
async def update_order_message(order_id: PydanticObjectId, data: models.OrderPullUpdate):
    order = await orders_flows.get(order_id)
    return await flows.update_order_message(order, data.config_names)


@router_api.post('/sheets/{order_id}', response_model=list[models.OrderMessage])
async def create_order_messages(order_id: str, data: models.OrderPullCreate):
    order = await orders_flows.get_by_order_id(order_id)
    return await flows.create_order_message(order, data.categories, data.config_names)


@router_api.delete('/sheets/{order_id}', response_model=list[models.OrderMessage])
async def delete_order_messages(order_id: str):
    order = await orders_flows.get_by_order_id(order_id)
    return await flows.delete_order_message(order)


@router_api.patch('/sheets/{order_id}', response_model=list[models.OrderMessage])
async def update_order_message(order_id: str, data: models.OrderPullUpdate):
    order = await orders_flows.get_by_order_id(order_id)
    return await flows.update_order_message(order, data.config_names)


router.include_router(router_api)
router.include_router(router_user)
