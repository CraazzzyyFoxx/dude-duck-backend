from fastapi import APIRouter, Depends
from beanie import PydanticObjectId

from app.core import enums
from app.services.auth import service as auth_service
from app.services.orders import flows as orders_flows

from . import models, flows, schemas, service

router = APIRouter(prefix='/accounting', tags=[enums.RouteTag.ACCOUNTING])


@router.patch('/boosters', response_model=list[models.UserOrder])
async def patch_boosters(
        model: models.SheetUserOrderCreate,
        _=Depends(auth_service.current_active_superuser_api)
):
    return await flows.update_boosters_percent(model)


@router.get("/{user_id}", response_model=models.UserAccountReport)
async def get_accounting_report(user=Depends(auth_service.resolve_user)):
    return await flows.create_user_report(user)


@router.get("/{user_id}/orders", response_model=list[schemas.UserOrderRead])
async def get_user_orders(user=Depends(auth_service.resolve_user)):
    return await service.get_by_user_id(user.id)


@router.get("/orders/{order_id}", response_model=list[schemas.UserOrderRead])
async def get_order_boosters(
        order_id: PydanticObjectId,
        user=Depends(auth_service.current_active_superuser)
):
    order = await orders_flows.get(order_id)
    return await service.get_by_order_id(order.id)


@router.post("/orders/{order_id}/close", response_model=models.CloseOrderForm, status_code=201)
async def send_close_request_order(
        order_id: PydanticObjectId,
        data: models.CloseOrderForm,
        user=Depends(auth_service.current_active_verified)
):
    order = await orders_flows.get(order_id)
    await flows.close_order(user, order, data)
    return data


@router.post("/orders/{order_id}/users/{user_id}", response_model=models.UserOrder)
async def paid_order(
        order_id: PydanticObjectId,
        user_id: PydanticObjectId,
        _=Depends(auth_service.current_active_superuser_api)
):
    order = await orders_flows.get(order_id)
    user = await auth_service.get_user(user_id)
    return await flows.paid_order(user, order)
