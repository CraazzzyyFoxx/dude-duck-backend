from beanie import PydanticObjectId
from fastapi import APIRouter, Depends

from app.core import enums
from app.services.auth import flows as auth_flows
from app.services.orders import flows as orders_flows

from . import flows, models, schemas, service

router = APIRouter(prefix='/accounting', tags=[enums.RouteTag.ACCOUNTING])


@router.get("/{user_id}", response_model=models.UserAccountReport)
async def get_accounting_report(user=Depends(auth_flows.resolve_user)):
    return await flows.create_user_report(user)


@router.get("/orders/{order_id}", response_model=list[schemas.UserOrderRead])
async def get_order_boosters(
        order_id: PydanticObjectId,
        _=Depends(auth_flows.current_active_superuser)
):
    order = await orders_flows.get(order_id)
    return await service.get_by_order_id(order.id)


@router.post("/orders/{order_id}", response_model=schemas.UserOrderRead)
async def create_order_booster(
        order_id: PydanticObjectId,
        data: schemas.OrderBoosterCreate,
        _=Depends(auth_flows.current_active_superuser)
):
    order = await orders_flows.get(order_id)
    user = await auth_flows.get_user(data.user_id)
    return await flows.add_booster(order, user)


@router.delete("/orders/{order_id}/{user_id}", response_model=schemas.UserOrderRead)
async def delete_order_booster(
        order_id: PydanticObjectId,
        user_id: PydanticObjectId,
        _=Depends(auth_flows.current_active_superuser)
):
    order = await orders_flows.get(order_id)
    user = await auth_flows.get_user(user_id)
    return await flows.remove_booster(order, user)


@router.post("/orders/{order_id}/close", response_model=models.CloseOrderForm, status_code=201)
async def send_close_request_order(
        order_id: PydanticObjectId,
        data: models.CloseOrderForm,
        user=Depends(auth_flows.current_active_verified)
):
    order = await orders_flows.get(order_id)
    await flows.close_order(user, order, data)
    return data


@router.post("/orders/{order_id}/users/{user_id}", response_model=models.UserOrderRead)
async def paid_order(
        order_id: PydanticObjectId,
        user_id: PydanticObjectId,
        _=Depends(auth_flows.current_active_superuser_api)
):
    order = await orders_flows.get(order_id)
    user = await auth_flows.get_user(user_id)
    return await flows.paid_order(user, order)
