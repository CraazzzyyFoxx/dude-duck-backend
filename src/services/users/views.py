from fastapi import APIRouter, Depends
from fastapi.responses import ORJSONResponse

from src import models, schemas
from src.core import db, enums, errors, pagination
from src.services.accounting import flows as accounting_flows
from src.services.auth import flows as auth_flows
from src.services.auth import service as auth_service
from src.services.integrations.notifications import flows as notifications_flows
from src.services.integrations.sheets import flows as sheets_flows
from src.services.order import flows as orders_flows
from src.services.payroll import service as payroll_service
from src.services.integrations.telegram import service as telegram_service

router = APIRouter(prefix="/users", tags=[enums.RouteTag.USERS])


@router.get("/@me", response_model=models.UserReadWithPayrolls)
async def get_me(user=Depends(auth_flows.current_active), session=Depends(db.get_async_session)):
    payrolls = await payroll_service.get_by_user_id(session, user.id)
    return models.UserReadWithPayrolls(
        **user.to_dict(),
        payrolls=[models.PayrollRead.model_validate(p, from_attributes=True) for p in payrolls],
    )


@router.get("/@me/payrolls", response_model=pagination.Paginated[models.PayrollRead])
async def get_my_payrolls(
    params: pagination.PaginationParams = Depends(),
    user=Depends(auth_flows.current_active),
    session=Depends(db.get_async_session),
):
    return await payroll_service.get_by_filter(session, user, params)


@router.patch("/@me", response_model=models.UserReadWithPayrolls)
async def update_me(
    user_update: models.UserUpdate,
    user=Depends(auth_flows.current_active),
    session=Depends(db.get_async_session),
):
    user = await auth_service.update(session, user, user_update, safe=True)
    user_read = await sheets_flows.create_or_update_user(session, user)
    return user_read


@router.post("/@me/generate-api-token")
async def generate_api_token(
    user=Depends(auth_flows.current_active_superuser),
    session=Depends(db.get_async_session),
):
    response = await auth_service.write_token_api(session, user)
    return ORJSONResponse({"access_token": response, "token_type": "bearer"})


@router.post("/@me/orders", response_model=pagination.Paginated[schemas.OrderReadActive])
async def filter_active_orders(
    params: schemas.OrderFilterParams = Depends(),
    user=Depends(auth_flows.current_active_verified),
    session=Depends(db.get_async_session),
):
    return await accounting_flows.get_by_filter(session, user, params)


@router.get("/@me/orders", response_model=schemas.OrderReadActive)
async def get_active_order(
    order_id: int,
    user=Depends(auth_flows.current_active_verified),
    session=Depends(db.get_async_session),
):
    order = await orders_flows.get(session, order_id)
    price = await accounting_flows.get_by_order_id_user_id(session, order, user)
    return await orders_flows.format_order_active(session, order, price)


@router.post("/@me/orders/close-request", response_model=schemas.OrderReadActive)
async def send_close_request(
    order_id: int,
    data: models.CloseOrderForm,
    user=Depends(auth_flows.current_active_verified),
    session=Depends(db.get_async_session),
):
    order = await orders_flows.get(session, order_id)
    new_order = await accounting_flows.close_order(session, user, order, data)
    price = await accounting_flows.get_by_order_id_user_id(session, new_order, user)
    return await orders_flows.format_order_active(session, new_order, price)


@router.get("/@me/payment/report", response_model=models.UserAccountReport)
async def get_accounting_report(
    user=Depends(auth_flows.current_active_verified),
    session=Depends(db.get_async_session),
):
    return await accounting_flows.create_user_report(session, user)


@router.post("/@me/request_verification", status_code=200)
async def request_verification(user=Depends(auth_flows.current_active)):
    if user.is_verified:
        raise errors.ApiHTTPException(
            status_code=400, detail=[errors.ApiException(code="already_verified", msg="User already verified")]
        )
    notifications_flows.send_request_verify(models.UserRead.model_validate(user))
    return ORJSONResponse({"detail": "ok"})


@router.get("/@me/telegram", response_model=models.TelegramAccountRead)
async def get_telegram(
    user=Depends(auth_flows.current_active),
    session=Depends(db.get_async_session),
):
    telegram_account = await telegram_service.get_tg_account(session, user.id)
    return models.TelegramAccountRead.model_validate(telegram_account, from_attributes=True)


@router.post("/@me/telegram", response_model=models.TelegramAccountRead)
async def connect_telegram(
    payload: models.TelegramAccountCreate,
    user=Depends(auth_flows.current_active),
    session=Depends(db.get_async_session),
):
    telegram_account = await telegram_service.connect_telegram(session, user, payload)
    return models.TelegramAccountRead.model_validate(telegram_account, from_attributes=True)


@router.delete("/@me/telegram", response_model=models.TelegramAccountRead)
async def disconnect_telegram(
    user=Depends(auth_flows.current_active),
    session=Depends(db.get_async_session),
):
    telegram_account = await telegram_service.disconnect_telegram(session, user)
    return models.TelegramAccountRead.model_validate(telegram_account, from_attributes=True)
