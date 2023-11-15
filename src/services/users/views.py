from fastapi import APIRouter, Depends, UploadFile
from starlette import status

from src.core import enums, errors, db, pagination
from src.services.accounting import flows as accounting_flows
from src.services.accounting import models as accounting_models
from src.services.auth import flows as auth_flows
from src.services.auth import models as auth_models
from src.services.auth import service as auth_service
from src.services.order import flows as orders_flows
from src.services.order import schemas as orders_schemas

from . import flows

router = APIRouter(prefix="/users", tags=[enums.RouteTag.USERS])


@router.get("/@me", response_model=auth_models.UserRead)
async def get_me(user=Depends(auth_flows.current_active)):
    return auth_models.UserRead.model_validate(user)


@router.patch("/@me", response_model=auth_models.UserRead)
async def update_me(
        user_update: auth_models.UserUpdate,
        user=Depends(auth_flows.current_active),
        session=Depends(db.get_async_session)
):
    return await flows.update_user(session, user_update, user)


@router.post("/@me/google-token", status_code=201, response_model=auth_models.AdminGoogleToken)
async def add_google_token(
        file: UploadFile, user=Depends(auth_flows.current_active_superuser), session=Depends(db.get_async_session)
):
    token = auth_models.AdminGoogleToken.model_validate_json(await file.read())
    await auth_service.update(session, user, auth_models.UserUpdateAdmin(google=token))
    return token


@router.get("/@me/google-token", response_model=auth_models.AdminGoogleToken)
async def read_google_token(user=Depends(auth_flows.current_active_superuser)):
    if user.google is None:
        raise errors.DDHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[errors.DDException(msg="Google Service account doesn't setup.", code="not_exist")],
        )
    return user.google


@router.post("/@me/generate-api-token")
async def generate_api_token(user=Depends(auth_flows.current_active_superuser), session=Depends(db.get_async_session)):
    response = await auth_service.write_token_api(session, user)
    return response


@router.get("/@me/orders", response_model=pagination.Paginated[orders_schemas.OrderReadActive])
async def get_active_orders(
    params: accounting_models.UserOrderFilterParams = Depends(),
    user=Depends(auth_flows.current_active_verified),
    session=Depends(db.get_async_session)
):
    if params.user_id and params.user_id != user.id and not user.is_superuser:
        raise errors.DDHTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=[errors.DDException(msg="You don't have permission to access.", code="forbidden")],
        )
    if params.user_id is None:
        params.user_id = user.id
    return await accounting_flows.get_by_filter(session, params)


@router.get("/@me/orders/{order_id}", response_model=orders_schemas.OrderReadActive)
async def get_active_order(
        order_id: int, user=Depends(auth_flows.current_active_verified), session=Depends(db.get_async_session)
):
    order = await orders_flows.get(session, order_id)
    price = await accounting_flows.get_by_order_id_user_id(session, order, user)
    return await orders_flows.format_order_active(session, order, price)


@router.post("/@me/orders/{order_id}/close-request", response_model=orders_schemas.OrderReadActive)
async def send_close_request(
    order_id: int,
    data: accounting_models.CloseOrderForm,
    user=Depends(auth_flows.current_active_verified),
    session=Depends(db.get_async_session)
):
    order = await orders_flows.get(session, order_id)
    new_order = await accounting_flows.close_order(session, user, order, data)
    price = await accounting_flows.get_by_order_id_user_id(session, new_order, user)
    return await orders_flows.format_order_active(session, new_order, price)


@router.get("/@me/payment/report", response_model=accounting_models.UserAccountReport)
async def get_accounting_report(
        user=Depends(auth_flows.current_active_verified),
        session=Depends(db.get_async_session)
):
    return await accounting_flows.create_user_report(session, user)
