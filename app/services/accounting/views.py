from beanie import PydanticObjectId
from fastapi import APIRouter, Depends

from app.core import enums
from app.services.auth import flows as auth_flows
from app.services.orders import flows as orders_flows

from . import flows, models, schemas, service

router = APIRouter(prefix="/accounting", tags=[enums.RouteTag.ACCOUNTING])


@router.get("/orders/{order_id}", response_model=list[schemas.UserOrderRead])
async def get_order_boosters(order_id: PydanticObjectId, _=Depends(auth_flows.current_active_superuser)):
    order = await orders_flows.get(order_id)
    return await service.get_by_order_id(order.id)


@router.post("/orders/{order_id}", response_model=schemas.UserOrderRead)
async def create_order_booster(
    order_id: PydanticObjectId,
    data: schemas.OrderBoosterCreate,
    _=Depends(auth_flows.current_active_superuser),
):
    order = await orders_flows.get(order_id)
    user = await auth_flows.get(data.user_id)
    if data.dollars:
        return await flows.add_booster_with_price(order, user, data.dollars)
    return await flows.add_booster(order, user)


@router.delete("/orders/{order_id}/{user_id}", response_model=models.UserOrder)
async def delete_order_booster(
    order_id: PydanticObjectId,
    user_id: PydanticObjectId,
    _=Depends(auth_flows.current_active_superuser),
):
    order = await orders_flows.get(order_id)
    user = await auth_flows.get(user_id)
    return await flows.remove_booster(order, user)


@router.post("/paid/{payment_id}", response_model=schemas.UserOrderRead)
async def paid_order(payment_id: PydanticObjectId, _=Depends(auth_flows.current_active_superuser_api)):
    return await flows.paid_order(payment_id)


@router.post("/report", response_model=schemas.AccountingReport)
async def generate_payment_report(
    data: schemas.AccountingReportSheetsForm, _=Depends(auth_flows.current_active_superuser)
):
    return await flows.create_report(
        data.start_date,
        data.end_date,
        data.first_sort,
        data.second_sort,
        data.spreadsheet,
        data.sheet_id,
        data.username,
    )
