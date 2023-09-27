from beanie import PydanticObjectId
from fastapi import APIRouter, Depends

from app.core import enums
from app.services.accounting import flows as accounting_flows
from app.services.accounting import models as accounting_models
from app.services.auth import flows as auth_flows
from app.services.auth import models as auth_models
from app.services.orders import flows as order_flows
from app.services.orders import schemas as order_schemas
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
    _: auth_flows.models.User = Depends(auth_flows.current_active_superuser),
):
    return await search_service.paginate(auth_models.User.all(), paging, sorting)


@router.get(path="/orders/{order_id}", response_model=order_schemas.OrderReadSystem)
async def get_order(order_id: PydanticObjectId):
    order = await order_flows.get(order_id)
    return await order_flows.format_order_system(order)


@router.get(path="/orders", response_model=search_service.models.Paginated[order_schemas.OrderReadSystem])
async def get_orders(
    paging: search_models.PaginationParams = Depends(),
    sorting: search_models.OrderSortingParams = Depends(),
):
    data = await order_flows.get_filter(paging, sorting)
    data["results"] = [await order_flows.format_order_system(order) for order in data["results"]]
    return data


@router.patch("/users/{user_id}", response_model=auth_models.UserRead)
async def update_user(user_update: auth_models.UserUpdateAdmin, user_id: PydanticObjectId):
    user = await auth_flows.get(user_id)
    return await user_flows.update_user(user_update, user)


@router.get("/users/{user_id}", response_model=auth_models.UserRead)
async def get_user(user_id: PydanticObjectId):
    user = await auth_flows.get(user_id)
    return auth_models.UserRead.model_validate(user)


@router.get("/users/{user_id}/payment/report", response_model=accounting_models.UserAccountReport)
async def get_accounting_report(user_id: PydanticObjectId):
    user = await auth_flows.get(user_id)
    return await accounting_flows.create_user_report(user)
