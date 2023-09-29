from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, UploadFile
from starlette import status

from app.core import enums, errors
from app.services.accounting import flows as accounting_flows
from app.services.accounting import models as accounting_models
from app.services.auth import flows as auth_flows
from app.services.auth import models as auth_models
from app.services.auth import service as auth_service
from app.services.orders import flows as orders_flows
from app.services.orders import models as orders_models
from app.services.orders import schemas as orders_schemas
from app.services.orders import service as orders_service
from app.services.search import models as search_models
from app.services.search import service as search_service

from . import flows

router = APIRouter(prefix="/users", tags=[enums.RouteTag.USERS])


@router.get("/@me", response_model=auth_models.UserRead)
async def get_me(user=Depends(auth_flows.current_active)):
    return auth_models.UserRead.model_validate(user)


@router.patch("/@me", response_model=auth_models.UserRead)
async def update_me(user_update: auth_models.UserUpdate, user=Depends(auth_flows.current_active)):
    return await flows.update_user(user_update, user)


@router.post("/@me/google-token", status_code=201, response_model=auth_models.AdminGoogleToken)
async def add_google_token(file: UploadFile, user=Depends(auth_flows.current_active_superuser)):
    token = auth_models.AdminGoogleToken.model_validate_json(await file.read())
    await auth_service.update(user, auth_models.UserUpdateAdmin(google=token))
    await user.save()
    return token.model_dump()


@router.get("/@me/google-token", response_model=auth_models.AdminGoogleToken)
async def read_google_token(user=Depends(auth_flows.current_active_superuser)):
    if user.google is None:
        raise errors.DudeDuckHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[errors.DudeDuckException(msg="Google Service account doesn't setup.", code="not_exist")],
        )
    return user.google


@router.post("/@me/generate-api-token")
async def generate_api_token(user=Depends(auth_flows.current_active_superuser)):
    response = await auth_service.write_token_api(user)
    return response


@router.get("/@me/orders", response_model=search_models.Paginated[orders_schemas.OrderReadActive])
async def get_active_orders(
    paging: search_models.PaginationParams = Depends(),
    sorting: search_models.OrderSortingParams = Depends(),
    user=Depends(auth_flows.current_active_verified),
):
    query = {"user_id": user.id}
    if sorting.completed != search_models.OrderSelection.ALL:
        if sorting.completed == search_models.OrderSelection.Completed:
            query["completed"] = True
        else:
            query["completed"] = False
    data = await search_service.paginate(accounting_models.UserOrder.find(query), paging, sorting)
    orders = await orders_service.get_by_ids([d.order_id.ref.id for d in data["results"]])
    orders_map: dict[PydanticObjectId, orders_models.Order] = {order.id: order for order in orders}
    results = [await orders_flows.format_order_active(orders_map[d.order_id.ref.id], d) for d in data["results"]]
    data["results"] = results
    return data


@router.get("/@me/orders/{order_id}", response_model=orders_schemas.OrderReadActive)
async def get_active_order(order_id: PydanticObjectId, user=Depends(auth_flows.current_active_verified)):
    order = await orders_flows.get(order_id)
    price = await accounting_flows.get_by_order_id_user_id(order, user)
    return await orders_flows.format_order_active(order, price)


@router.post("/@me/orders/{order_id}/close-request", response_model=orders_schemas.OrderReadActive)
async def send_close_request(
    order_id: PydanticObjectId,
    data: accounting_models.CloseOrderForm,
    user=Depends(auth_flows.current_active_verified),
):
    order = await orders_flows.get(order_id)
    new_order = await accounting_flows.close_order(user, order, data)

    price = await accounting_flows.get_by_order_id_user_id(new_order, user)
    return await orders_flows.format_order_active(new_order, price)


@router.get("/@me/payment/report", response_model=accounting_models.UserAccountReport)
async def get_accounting_report(user=Depends(auth_flows.current_active_verified)):
    return await accounting_flows.create_user_report(user)
