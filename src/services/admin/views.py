import sqlalchemy as sa
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from sqlalchemy.sql.functions import count

from src import models, schemas
from src.core import db, enums, pagination
from src.services.auth import flows as auth_flows
from src.services.auth import service as auth_service
from src.services.integrations.notifications import \
    flows as notifications_flows
from src.services.integrations.sheets import flows as sheets_flows
from src.services.order import flows as orders_flows
from src.services.payroll import service as payroll_service

router = APIRouter(
    prefix="/admin",
    tags=[enums.RouteTag.ADMIN],
    dependencies=[Depends(auth_flows.current_active_superuser)],
)


@router.get("/users/filter", response_model=pagination.Paginated[models.UserRead])
async def get_users(
    params: pagination.PaginationParams = Depends(),
    session: AsyncSession = Depends(db.get_async_session),
):
    query = sa.select(models.User).offset(params.offset).limit(params.limit).order_by(params.order_by)
    result = await session.execute(query)
    results = [models.UserRead.model_validate(user) for user in result.scalars()]
    total = await session.execute(sa.select(count(models.User.id)))
    return pagination.Paginated(
        page=params.page,
        per_page=params.per_page,
        total=total.one()[0],
        results=results,
    )


@router.get(path="/orders/{order_id}", response_model=schemas.OrderReadSystem)
async def get_order(order_id: int, session=Depends(db.get_async_session)):
    order = await orders_flows.get(session, order_id)
    return await orders_flows.format_order_system(session, order)


@router.patch("/users/{user_id}", response_model=models.UserReadWithPayrolls)
async def update_user(
    user_update: models.UserUpdateAdmin,
    user_id: int,
    session=Depends(db.get_async_session),
):
    user = await auth_flows.get(session, user_id)
    updated_user = await auth_service.update(session, user, user_update)
    user_with_payrolls = await sheets_flows.create_or_update_user(session, updated_user)
    return user_with_payrolls


@router.get("/users/{user_id}", response_model=models.UserReadWithPayrolls)
async def get_user(user_id: int, session=Depends(db.get_async_session)):
    user = await auth_flows.get(session, user_id)
    payrolls = await payroll_service.get_by_user_id(session, user.id)
    return models.UserReadWithPayrolls(
        **user.to_dict(),
        payrolls=[models.PayrollRead.model_validate(p, from_attributes=True) for p in payrolls],
    )


@router.post("/users/{user_id}/verify", response_model=models.UserRead)
async def verify_user(user_id: int, session=Depends(db.get_async_session)):
    user = await auth_flows.get(session, user_id)
    updated_user = await auth_service.verify(session, user)
    updated_user_read = models.UserRead.model_validate(updated_user)
    notifications_flows.send_verified_notify(updated_user_read)
    await sheets_flows.create_or_update_user(session, updated_user)
    return updated_user_read


@router.post("/users/{user_id}/payroll", response_model=models.PayrollRead)
async def create_payroll(
    payroll_create: models.PayrollCreate,
    user_id: int,
    session=Depends(db.get_async_session),
):
    user = await auth_flows.get(session, user_id)
    payroll = await payroll_service.create(session, user, payroll_create)
    await sheets_flows.create_or_update_user(session, user)
    return payroll


@router.patch("/users/{user_id}/payroll", response_model=models.PayrollRead)
async def update_payroll(
    payroll_update: models.PayrollUpdate,
    user_id: int,
    payroll_id: int,
    session=Depends(db.get_async_session),
):
    user = await auth_flows.get(session, user_id)
    payroll = await payroll_service.update(session, payroll_id, payroll_update)
    await sheets_flows.create_or_update_user(session, user)
    return payroll


@router.delete("/users/{user_id}/payroll", response_model=models.PayrollRead)
async def delete_payroll(user_id: int, payroll_id: int, session=Depends(db.get_async_session)):
    user = await auth_flows.get(session, user_id)
    payroll = await payroll_service.delete(session, payroll_id)
    await sheets_flows.create_or_update_user(session, user)
    return payroll


@router.get(
    "/users/{user_id}/payroll/filter",
    response_model=pagination.Paginated[models.PayrollRead],
)
async def get_payrolls(
    user_id: int,
    params: pagination.PaginationParams = Depends(),
    session=Depends(db.get_async_session),
):
    user = await auth_flows.get(session, user_id)
    return await payroll_service.get_by_filter(session, user, params)


@router.post(
    path="/orders/filter",
    response_model=pagination.Paginated[schemas.OrderReadSystem],
)
async def get_orders(params: schemas.OrderFilterParams, session=Depends(db.get_async_session)):
    query = sa.select(models.Order).options(
        joinedload(models.Order.info),
        joinedload(models.Order.price),
        joinedload(models.Order.credentials),
        joinedload(models.Order.screenshots),
    )

    query = params.apply_filters(query)
    query = params.apply_pagination(query)
    result = await session.execute(query)
    results = [await orders_flows.format_order_system(session, order) for order in result.unique().scalars()]
    count_query = params.apply_filters(sa.select(count(models.Order.id)))
    total = await session.execute(count_query)
    return pagination.Paginated(
        page=params.page,
        per_page=params.per_page,
        total=total.one()[0],
        results=results,
    )
