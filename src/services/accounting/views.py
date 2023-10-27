from fastapi import APIRouter, Depends

from src.core import enums, db
from src.services.auth import flows as auth_flows
from src.services.orders import flows as orders_flows

from . import flows, models, service

router = APIRouter(
    prefix="/accounting", tags=[enums.RouteTag.ACCOUNTING], dependencies=[Depends(auth_flows.current_active_superuser)]
)


@router.get("/orders/{order_id}", response_model=list[models.UserOrderRead])
async def get_order_boosters(order_id: int, session=Depends(db.get_async_session)):
    order = await orders_flows.get(session, order_id)
    return await service.get_by_order_id(session, order.id)


@router.post("/orders/{order_id}", response_model=models.UserOrderRead)
async def create_order_booster(order_id: int, data: models.OrderBoosterCreate, session=Depends(db.get_async_session)):
    order = await orders_flows.get(session, order_id)
    user = await auth_flows.get(session, data.user_id)
    if data.dollars:
        return await flows.add_booster_with_price(session, order, user, data.dollars)
    return await flows.add_booster(session, order, user)


@router.patch("/orders/{order_id}/{user_id}", response_model=models.UserOrderRead)
async def patch_order_booster(
        order_id: int, user_id: int, data: models.UserOrderUpdate, session=Depends(db.get_async_session)
):
    order = await orders_flows.get(session, order_id)
    user = await auth_flows.get(session, user_id)
    if data.dollars:
        return await flows.add_booster_with_price(session, order, user, data.dollars)
    return await flows.add_booster(session, order, user)


@router.delete("/orders/{order_id}/{user_id}", response_model=models.UserOrderRead)
async def delete_order_booster(order_id: int, user_id: int, session=Depends(db.get_async_session)):
    order = await orders_flows.get(session, order_id)
    user = await auth_flows.get(session, user_id)
    return await flows.remove_booster(session, order, user)


@router.post("/paid/{payment_id}", response_model=models.UserOrderRead)
async def paid_order(payment_id: int, session=Depends(db.get_async_session)):
    return await flows.paid_order(session, payment_id)


@router.post("/report", response_model=models.AccountingReport)
async def generate_payment_report(data: models.AccountingReportSheetsForm):
    return await flows.create_report(
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
