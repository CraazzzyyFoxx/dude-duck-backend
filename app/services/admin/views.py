from fastapi import APIRouter, Depends
from tortoise.expressions import Q

from app.core import enums
from app.services.accounting import flows as accounting_flows
from app.services.accounting import models as accounting_models
from app.services.auth import flows as auth_flows
from app.services.auth import models as auth_models
from app.services.orders import flows as orders_flows
from app.services.orders import models as orders_models
from app.services.orders import schemas as order_schemas
from app.services.orders import schemas as orders_schemas
from app.services.orders import service as orders_service
from app.services.search import models as search_models
from app.services.search import service as search_service
from app.services.users import flows as user_flows

router = APIRouter(
    prefix="/admin", tags=[enums.RouteTag.ADMIN], dependencies=[Depends(auth_flows.current_active_superuser)]
)


@router.get("/users", response_model=search_models.Paginated[auth_models.UserRead])
async def get_users(
    paging: search_models.PaginationParams = Depends(),
    sorting: search_models.SortingParams = Depends(),
    _: auth_models.User = Depends(auth_flows.current_active_superuser),
):
    return await search_service.paginate(auth_models.User.all(), paging, sorting)


@router.get(path="/orders/{order_id}", response_model=order_schemas.OrderReadSystem)
async def get_order(order_id: int):
    order = await orders_flows.get(order_id)
    return await orders_flows.format_order_system(order)


@router.get(path="/orders", response_model=search_models.Paginated[order_schemas.OrderReadSystem])
async def get_orders(
    paging: search_models.PaginationParams = Depends(),
    sorting: search_models.OrderSortingParams = Depends(),
):
    data = await orders_flows.get_filter(paging, sorting)
    data["results"] = [await orders_flows.format_order_system(order) for order in data["results"]]
    return data


@router.patch("/users/{user_id}", response_model=auth_models.UserRead)
async def update_user(user_update: auth_models.UserUpdateAdmin, user_id: int):
    user = await auth_flows.get(user_id)
    return await user_flows.update_user(user_update, user)


@router.get("/users/{user_id}", response_model=auth_models.UserRead)
async def get_user(user_id: int):
    user = await auth_flows.get(user_id)
    return auth_models.UserRead.model_validate(user)


@router.get("/users/{user_id}/payment/report", response_model=accounting_models.UserAccountReport)
async def get_accounting_report(user_id: int):
    user = await auth_flows.get(user_id)
    return await accounting_flows.create_user_report(user)


@router.get("/users/{user_id}/orders", response_model=search_models.Paginated[orders_schemas.OrderReadActive])
async def get_active_orders(
    user_id: int,
    paging: search_models.PaginationParams = Depends(),
    sorting: search_models.OrderSortingParams = Depends(),
):
    user = await auth_flows.get(user_id)
    query = [Q(user_id=user.id)]
    if sorting.completed != search_models.OrderSelection.ALL:
        if sorting.completed == search_models.OrderSelection.Completed:
            query.append(Q(completed=True))
        else:
            query.append(Q(completed=False))
    data = await search_service.paginate(accounting_models.UserOrder.filter(Q(*query)), paging, sorting)
    orders = await orders_service.get_by_ids([d.order_id for d in data["results"]], prefetch=True)
    orders_map: dict[int, orders_models.Order] = {order.id: order for order in orders}
    results = [await orders_flows.format_order_active(orders_map[d.order_id], d) for d in data["results"]]
    data["results"] = results
    return data
