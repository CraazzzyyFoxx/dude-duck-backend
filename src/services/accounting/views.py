from fastapi import APIRouter, Depends

from src import models, schemas
from src.core import db, enums, pagination
from src.services.auth import flows as auth_flows
from src.services.order import flows as order_flows

from . import flows, service

router = APIRouter(
    prefix="/accounting",
    tags=[enums.RouteTag.ACCOUNTING],
    dependencies=[Depends(auth_flows.current_active_superuser)],
)


@router.get("/orders", response_model=list[models.UserOrderRead])
async def get_order_boosters(order_id: int, session=Depends(db.get_async_session)):
    order = await order_flows.get(session, order_id)
    return await service.get_by_order_id(session, order.id)


@router.post("/orders", response_model=models.UserOrderRead)
async def create_order_booster(order_id: int, data: models.UserOrderCreate, session=Depends(db.get_async_session)):
    order = await order_flows.get(session, order_id)
    user = await auth_flows.get(session, data.user_id)
    if data.dollars:
        return await flows.add_booster_with_price(session, order, user, data.dollars)
    return await flows.add_booster(session, order, user)


@router.put("/orders", response_model=models.UserOrderRead)
async def update_order_booster(
    order_id: int,
    user_id: int,
    data: models.UserOrderUpdate,
    session=Depends(db.get_async_session),
):
    order = await order_flows.get(session, order_id)
    user = await auth_flows.get(session, user_id)
    return await service.update(session, order, user, data)


@router.delete("/orders", response_model=models.UserOrderRead)
async def delete_order_booster(order_id: int, user_id: int, session=Depends(db.get_async_session)):
    order = await order_flows.get(session, order_id)
    user = await auth_flows.get(session, user_id)
    return await service.delete(session, order, user)


@router.get("/report", response_model=models.AccountingReport)
async def generate_payment_report(
    data: models.AccountingReportSheetsForm = Depends(),
    session=Depends(db.get_async_session),
):
    return await flows.create_report(
        session,
        data.start_date,
        data.end_date,
        data.first_sort,
        data.second_sort,
        data.spreadsheet,
        data.sheet_id,
        data.username,
        data.is_completed,
        data.is_paid,
    )


@router.get("/users/{user_id}/payment/report", response_model=models.UserAccountReport)
async def get_accounting_report(user_id: int, session=Depends(db.get_async_session)):
    user = await auth_flows.get(session, user_id)
    return await flows.create_user_report(session, user)


@router.post(
    "/users/{user_id}/orders",
    response_model=pagination.Paginated[schemas.OrderReadActive],
)
async def get_active_orders(
    user_id: int,
    params: schemas.OrderFilterParams = Depends(),
    session=Depends(db.get_async_session),
):
    user = await auth_flows.get(session, user_id)
    return await flows.get_by_filter(session, user, params)
