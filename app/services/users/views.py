from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi_users import exceptions
from fastapi_users.router import ErrorCode
from starlette import status
from starlette.requests import Request
from starlette.responses import Response

from app.core.enums import RouteTag
from app.services.auth import flows as auth_flows
from app.services.auth import service as auth_service
from app.services.auth import manager as auth_manager
from app.services.auth import utils as auth_utils
from app.services.auth import models as auth_models
from app.services.accounting import service as accounting_service
from app.services.accounting import models as accounting_models
from app.services.search import service as search_service
from app.services.orders import flows as orders_flows
from app.services.orders import schemas as orders_schemas
from app.services.preorders import flows as preorders_flows
from app.services.preorders import models as preorders_models
from app.services.permissions import service as permissions_service

router = APIRouter(prefix="/users", tags=[RouteTag.USERS])


@router.get("/{user_id}", response_model=auth_service.models.UserRead)
async def get_me(user=Depends(auth_flows.resolve_user)):
    return auth_service.models.UserRead.model_validate(user)


@router.get("", response_model=search_service.models.Paginated[auth_models.UserRead])
async def get_users(
        paging: search_service.models.PaginationParams = Depends(),
        sorting: search_service.models.SortingParams = Depends(),
        _: auth_flows.models.User = Depends(auth_flows.current_active_superuser)
):
    return await search_service.paginate(auth_models.User.find({}), paging, sorting)


@router.patch("/@me", response_model=auth_service.models.UserRead)
async def update_user(user_update: auth_service.models.UserUpdate, request: Request,
                      user=Depends(auth_flows.current_active_verified),
                      user_manager: auth_manager.UserManager = Depends(auth_flows.get_user_manager)):
    try:
        user = await user_manager.update(
            user_update, user, safe=True, request=request
        )
        return auth_service.models.UserRead.model_validate(user, from_attributes=True)
    except exceptions.InvalidPasswordException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": ErrorCode.UPDATE_USER_INVALID_PASSWORD,
                "reason": e.reason,
            },
        )
    except exceptions.UserAlreadyExists:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=ErrorCode.UPDATE_USER_EMAIL_ALREADY_EXISTS,
        )


@router.patch("/{user_id}", response_model=auth_service.models.UserRead)
async def update_user(user_update: auth_service.models.UserUpdateAdmin, request: Request,
                      user_id: PydanticObjectId,
                      _=Depends(auth_flows.current_active_superuser),
                      user_manager: auth_manager.UserManager = Depends(auth_flows.get_user_manager)):
    user = await auth_flows.get_user(user_id)

    try:
        user = await user_manager.update(
            user_update, user, safe=True, request=request
        )
        return auth_service.models.UserRead.model_validate(user, from_attributes=True)
    except exceptions.InvalidPasswordException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": ErrorCode.UPDATE_USER_INVALID_PASSWORD,
                "reason": e.reason,
            },
        )
    except exceptions.UserAlreadyExists:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=ErrorCode.UPDATE_USER_EMAIL_ALREADY_EXISTS,
        )


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response,
               dependencies=[Depends(auth_flows.current_active_superuser)])
async def delete_user(
        user=Depends(auth_flows.resolve_user),
        user_manager: auth_manager.UserManager = Depends(auth_flows.get_user_manager)
):
    await user_manager.delete(user)
    return None


@router.post("/@me/google-token", status_code=201, response_model=auth_service.models.AdminGoogleToken)
async def add_google_token(file: UploadFile, user=Depends(auth_flows.current_active_superuser)):
    token = auth_service.models.AdminGoogleToken.model_validate_json(await file.read())
    user.google = token
    await user.save_changes()
    return user.google


@router.get("/@me/google-token", response_model=auth_service.models.AdminGoogleToken)
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


@router.get("/{user_id}/orders",
            response_model=search_service.models.Paginated[orders_schemas.OrderReadUser])
async def get_user_orders(
        paging: search_service.models.PaginationParams = Depends(),
        sorting: search_service.models.OrderSortingParams = Depends(),
        user=Depends(auth_flows.resolve_user)
):
    query = {"user_id": user.id}
    if sorting.completed != search_service.models.OrderSelection.ALL:
        if sorting.completed == search_service.models.OrderSelection.Completed:
            query["completed"] = True
        else:
            query["completed"] = False
    data = await search_service.paginate(accounting_models.UserOrder.find(query), paging, sorting)
    results = []
    for d in data["results"]:
        order = await orders_flows.get(d.order_id)
        results.append(await permissions_service.format_order_active(order, user, d))
    data["results"] = results
    return data


@router.get("/{user_id}/orders/{order_id}", response_model=orders_schemas.OrderReadUser)
async def get_user_order(order_id: PydanticObjectId, user=Depends(auth_flows.resolve_user)):
    price = await accounting_service.get_by_order_id_user_id(order_id, user.id)
    order = await orders_flows.get(order_id)
    return await permissions_service.format_order_active(order, user, price)


@router.get("/{user_id}/orders/{order_id}/telegram", response_model=orders_schemas.OrderReadUser)
async def get_user_order_telegram(order_id: PydanticObjectId, _=Depends(auth_flows.resolve_user)):
    return await permissions_service.format_order(await orders_flows.get(order_id), None)


@router.get("/{user_id}/preorders/{order_id}/telegram", response_model=preorders_models.PreOrderRead)
async def get_user_order_telegram(order_id: PydanticObjectId, _=Depends(auth_flows.resolve_user)):
    return await preorders_flows.get(order_id)
