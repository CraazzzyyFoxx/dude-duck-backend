import sqlalchemy as sa

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.functions import count

from src.core import enums, db, pagination
from src.services.accounting import flows as accounting_flows
from src.services.accounting import models as accounting_models
from src.services.auth import flows as auth_flows
from src.services.auth import models as auth_models
from src.services.order import flows as orders_flows
from src.services.order import models as orders_models
from src.services.order import schemas as order_schemas
from src.services.order import schemas as orders_schemas
from src.services.users import flows as user_flows

router = APIRouter(
    prefix="/admin", tags=[enums.RouteTag.ADMIN], dependencies=[Depends(auth_flows.current_active_superuser)]
)


@router.get("/users", response_model=pagination.Paginated[auth_models.UserRead])
async def get_users(
    params: pagination.PaginationParams = Depends(), session: AsyncSession = Depends(db.get_async_session)
):
    query = sa.select(auth_models.User).offset(params.offset).limit(params.limit).order_by(params.order_by)
    result = await session.execute(query)
    results = [auth_models.UserRead.model_validate(user) for user in result.scalars()]
    total = await session.execute(sa.select(count(auth_models.User.id)))
    return pagination.Paginated(page=params.page, per_page=params.per_page, total=total.first()[0], results=results)


@router.get(path="/orders/{order_id}", response_model=order_schemas.OrderReadSystem)
async def get_order(order_id: int, session=Depends(db.get_async_session)):
    order = await orders_flows.get(session, order_id)
    return await orders_flows.format_order_system(session, order)


@router.get(path="/orders", response_model=pagination.Paginated[order_schemas.OrderReadSystem])
async def get_orders(paging: order_schemas.OrderFilterParams = Depends(), session=Depends(db.get_async_session)):
    data = await orders_flows.get_by_filter(session, paging)
    data["results"] = [await orders_flows.format_order_system(session, order) for order in data["results"]]
    return data


@router.patch("/users/{user_id}", response_model=auth_models.UserRead)
async def update_user(user_update: auth_models.UserUpdateAdmin, user_id: int, session=Depends(db.get_async_session)):
    user = await auth_flows.get(session, user_id)
    return await user_flows.update_user(session, user_update, user)


@router.get("/users/{user_id}", response_model=auth_models.UserRead)
async def get_user(user_id: int, session=Depends(db.get_async_session)):
    user = await auth_flows.get(session, user_id)
    return auth_models.UserRead.model_validate(user)


@router.get("/users/{user_id}/payment/report", response_model=accounting_models.UserAccountReport)
async def get_accounting_report(user_id: int, session=Depends(db.get_async_session)):
    user = await auth_flows.get(session, user_id)
    return await accounting_flows.create_user_report(session, user)


@router.get("/users/{user_id}/orders", response_model=pagination.Paginated[orders_schemas.OrderReadActive])
async def get_active_orders(
    user_id: int, params: pagination.PaginationParams = Depends(), session=Depends(db.get_async_session)
):
    user = await auth_flows.get(session, user_id)
    query = (
        sa.select(accounting_models.UserOrder, orders_models.Order)
        .where(accounting_models.UserOrder.user_id == user.id)
        .join(orders_models.Order.id == accounting_models.UserOrder.order_id)
        .offset(params.offset)
        .limit(params.limit)
        .order_by(params.order_by)
    )
    result = await session.execute(query)
    total = await session.execute(
        sa.select(count(accounting_models.UserOrder.id))
        .where(accounting_models.UserOrder.user_id == user.id)
    )
    results = []
    for row in result:
        results.append(await orders_flows.format_order_active(session, row[1], row[0]))
    return pagination.Paginated(page=params.page, per_page=params.per_page, total=total.first()[0], results=results)
