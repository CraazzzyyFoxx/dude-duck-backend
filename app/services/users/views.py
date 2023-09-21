from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, HTTPException, UploadFile
from starlette import status
from starlette.requests import Request

from app.core.enums import RouteTag
from app.services.accounting import flows as accounting_flows
from app.services.accounting import models as accounting_models
from app.services.auth import flows as auth_flows
from app.services.auth import manager as auth_manager
from app.services.auth import models as auth_models
from app.services.auth import utils as auth_utils
from app.services.orders import flows as orders_flows
from app.services.orders import models as orders_models
from app.services.orders import schemas as orders_schemas
from app.services.orders import service as orders_service
from app.services.search import models as search_models
from app.services.search import service as search_service

from . import flows

router = APIRouter(prefix="/users", tags=[RouteTag.USERS])


@router.get("", response_model=search_models.Paginated[auth_models.UserRead])
async def get_users(
        paging: search_models.PaginationParams = Depends(),
        sorting: search_models.SortingParams = Depends(),
        _: auth_flows.models.User = Depends(auth_flows.current_active_superuser)
):
    return await search_service.paginate(auth_models.User.find({}), paging, sorting)


@router.get("/@me", response_model=auth_models.UserRead)
async def get_me(user=Depends(auth_flows.current_active_verified)):
    return auth_models.UserRead.model_validate(user)


@router.patch("/@me", response_model=auth_models.UserRead)
async def update_me(user_update: auth_models.UserUpdate, request: Request,
                    user=Depends(auth_flows.current_active_verified),
                    user_manager: auth_manager.UserManager = Depends(auth_flows.get_user_manager)):
    return await flows.update_user(request, user_update, user, user_manager)


@router.patch("/{user_id}", response_model=auth_models.UserRead)
async def update_user(user_update: auth_models.UserUpdateAdmin, request: Request,
                      user_id: PydanticObjectId,
                      _=Depends(auth_flows.current_active_superuser),
                      user_manager: auth_manager.UserManager = Depends(auth_flows.get_user_manager)):
    user = await auth_flows.get_user(user_id)
    return await flows.update_user(request, user_update, user, user_manager)


@router.get("/{user_id}", response_model=auth_models.UserRead)
async def get_user(user_id: PydanticObjectId, _=Depends(auth_flows.current_active_superuser)):
    user = await auth_flows.get_user(user_id)
    return auth_models.UserRead.model_validate(user)


@router.post("/@me/google-token", status_code=201, response_model=auth_models.AdminGoogleToken)
async def add_google_token(file: UploadFile, user=Depends(auth_flows.current_active_superuser)):
    token = auth_models.AdminGoogleToken.model_validate_json(await file.read())
    user.google = token
    await user.save_changes()
    return user.google


@router.get("/@me/google-token", response_model=auth_models.AdminGoogleToken)
async def read_google_token(user=Depends(auth_flows.current_active_superuser)):
    if user.google is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail=[{"msg": "Google Service account doesn't setup."}])
    return user.google


@router.post("/@me/generate-api-token")
async def generate_api_token(
        user=Depends(auth_flows.current_active_superuser),
        strategy=Depends(auth_utils.auth_backend_api.get_strategy)
):
    response = await auth_utils.auth_backend_api.login(strategy, user)
    return response


@router.get("/@me/orders",
            response_model=search_models.Paginated[orders_schemas.OrderReadActive])
async def get_active_orders(
        paging: search_models.PaginationParams = Depends(),
        sorting: search_models.OrderSortingParams = Depends(),
        user=Depends(auth_flows.current_active_verified)
):
    query = {"user_id": user.id}
    if sorting.completed != search_models.OrderSelection.ALL:
        if sorting.completed == search_models.OrderSelection.Completed:
            query["completed"] = True
        else:
            query["completed"] = False
    data = await search_service.paginate(accounting_models.UserOrder.find(query), paging, sorting)
    orders = await orders_service.get_by_ids([d.order_id for d in data["results"]])
    orders_map: dict[PydanticObjectId, orders_models.Order] = {order.id: order for order in orders}
    results = [await orders_flows.format_order_active(orders_map[d.order_id], d) for d in data["results"]]
    data["results"] = results
    return data


@router.get("/@me/orders/{order_id}", response_model=orders_schemas.OrderReadActive)
async def get_active_order(
        order_id: PydanticObjectId,
        user=Depends(auth_flows.current_active_verified)
):
    order = await orders_flows.get(order_id)
    price = await accounting_flows.get_by_order_id_user_id(order, user)
    return await orders_flows.format_order_active(order, price)


@router.post("/@me/orders/{order_id}/close-request", response_model=orders_schemas.OrderReadActive)
async def send_close_request(
        order_id: PydanticObjectId,
        data: accounting_models.CloseOrderForm,
        user=Depends(auth_flows.current_active_verified)):
    order = await orders_flows.get(order_id)
    new_order = await accounting_flows.close_order(user, order, data)

    price = await accounting_flows.get_by_order_id_user_id(new_order, user.id)
    return await orders_flows.format_order_active(new_order, price)


@router.get("/@me/payment/report", response_model=accounting_models.UserAccountReport)
async def get_accounting_report(user=Depends(auth_flows.current_active_verified)):
    return await accounting_flows.create_user_report(user)
