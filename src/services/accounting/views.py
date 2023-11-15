from fastapi import APIRouter, Depends

from src.core import enums, db
from src.services.auth import flows as auth_flows
from src.services.order import flows as orders_flows

from . import flows, models, service

router = APIRouter(
    prefix="/accounting", tags=[enums.RouteTag.ACCOUNTING], dependencies=[Depends(auth_flows.current_active_superuser)]
)


@router.get("/orders", response_model=list[models.UserOrderRead])
async def get_order_boosters(order_id: int, session=Depends(db.get_async_session)):
    order = await orders_flows.get(session, order_id)
    return await service.get_by_order_id(session, order.id)


@router.post("/orders", response_model=models.UserOrderRead)
async def create_order_booster(order_id: int, data: models.UserOrderCreate, session=Depends(db.get_async_session)):
    order = await orders_flows.get(session, order_id)
    user = await auth_flows.get(session, data.user_id)
    if data.dollars:
        return await flows.add_booster_with_price(session, order, user, data.dollars)
    return await flows.add_booster(session, order, user)


@router.put("/orders", response_model=models.UserOrderRead)
async def update_order_booster(
        order_id: int, user_id: int, data: models.UserOrderUpdate, session=Depends(db.get_async_session)
):
    order = await orders_flows.get(session, order_id)
    user = await auth_flows.get(session, user_id)
    return await service.update(session, order, user, data)


@router.delete("/orders", response_model=models.UserOrderRead)
async def delete_order_booster(order_id: int, user_id: int, session=Depends(db.get_async_session)):
    order = await orders_flows.get(session, order_id)
    user = await auth_flows.get(session, user_id)
    return await service.delete(session, order, user)


@router.get("/report", response_model=models.AccountingReport)
async def generate_payment_report(
        data: models.AccountingReportSheetsForm = Depends(), session=Depends(db.get_async_session)
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
