import sqlalchemy as sa
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.functions import count

from src.core import db, enums, pagination
from src.services.auth import flows as auth_flows
from src.services.auth import models as auth_models
from src.services.order import flows as orders_flows
from src.services.order import schemas as order_schemas
from src.services.payroll import models as payroll_models
from src.services.payroll import service as payroll_service
from src.services.users import flows as user_flows
from src.services.users import models as user_models

router = APIRouter(
    prefix="/admin", tags=[enums.RouteTag.ADMIN], dependencies=[Depends(auth_flows.current_active_superuser)]
)


@router.get("/users/filter", response_model=pagination.Paginated[auth_models.UserRead])
async def get_users(
    params: pagination.PaginationParams = Depends(), session: AsyncSession = Depends(db.get_async_session)
):
    query = sa.select(auth_models.User).offset(params.offset).limit(params.limit).order_by(params.order_by)
    result = await session.execute(query)
    results = [auth_models.UserRead.model_validate(user) for user in result.scalars()]
    total = await session.execute(sa.select(count(auth_models.User.id)))
    return pagination.Paginated(page=params.page, per_page=params.per_page, total=total.one()[0], results=results)


@router.get(path="/orders/{order_id}", response_model=order_schemas.OrderReadSystem)
async def get_order(order_id: int, session=Depends(db.get_async_session)):
    order = await orders_flows.get(session, order_id)
    return await orders_flows.format_order_system(session, order)


@router.post(path="/orders/filter", response_model=pagination.Paginated[order_schemas.OrderReadSystem])
async def get_orders(paging: order_schemas.OrderFilterParams = Depends(), session=Depends(db.get_async_session)):
    return await orders_flows.get_by_filter(session, paging)


@router.patch("/users/{user_id}", response_model=user_models.UserReadWithPayrolls)
async def update_user(user_update: auth_models.UserUpdateAdmin, user_id: int, session=Depends(db.get_async_session)):
    user = await auth_flows.get(session, user_id)
    updated_user = await user_flows.update_user(session, user_update, user)
    payrolls = await payroll_service.get_by_user_id(session, user.id)
    return user_models.UserReadWithPayrolls(
        **updated_user.model_dump(),
        payrolls=[payroll_models.PayrollRead.model_validate(p, from_attributes=True) for p in payrolls],
    )


@router.get("/users/{user_id}", response_model=user_models.UserReadWithPayrolls)
async def get_user(user_id: int, session=Depends(db.get_async_session)):
    user = await auth_flows.get(session, user_id)
    payrolls = await payroll_service.get_by_user_id(session, user.id)
    return user_models.UserReadWithPayrolls(
        **user.to_dict(),
        payrolls=[payroll_models.PayrollRead.model_validate(p, from_attributes=True) for p in payrolls],
    )


@router.post("/users/{user_id}/payroll", response_model=payroll_models.PayrollRead)
async def create_payroll(
    payroll_create: payroll_models.PayrollCreate,
    user_id: int,
    session=Depends(db.get_async_session),
):
    user = await auth_flows.get(session, user_id)
    return await payroll_service.create(session, user, payroll_create)


@router.patch("/users/{user_id}/payroll", response_model=payroll_models.PayrollRead)
async def update_payroll(
    payroll_update: payroll_models.PayrollUpdate,
    user_id: int,
    payroll_id: int,
    session=Depends(db.get_async_session),
):
    _ = await auth_flows.get(session, user_id)
    return await payroll_service.update(session, payroll_id, payroll_update)


@router.delete("/users/{user_id}/payroll", response_model=payroll_models.PayrollRead)
async def delete_payroll(user_id: int, payroll_id: int, session=Depends(db.get_async_session)):
    _ = await auth_flows.get(session, user_id)
    return await payroll_service.delete(session, payroll_id)


@router.get("/users/{user_id}/payroll/filter", response_model=pagination.Paginated[payroll_models.PayrollRead])
async def get_payrolls(
    user_id: int,
    params: pagination.PaginationParams = Depends(),
    session=Depends(db.get_async_session),
):
    user = await auth_flows.get(session, user_id)
    return await payroll_service.get_by_filter(session, user, params)
