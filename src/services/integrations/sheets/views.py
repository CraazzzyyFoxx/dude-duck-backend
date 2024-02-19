import sqlalchemy as sa
from fastapi import APIRouter, Depends, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.functions import count

from src import models, schemas
from src.core import db, enums, errors, pagination
from src.services.accounting import flows as accounting_flows
from src.services.auth import flows as auth_flows
from src.services.integrations.message import service as message_service
from src.services.integrations.notifications import flows as notifications_flows
from src.services.order import flows as order_flows
from src.services.order import flows as orders_flows
from src.services.order import service as orders_service
from src.services.preorder import flows as preorder_flows
from src.services.preorder import service as preorder_service

from . import flows, service

router = APIRouter(prefix="/integrations/sheets", tags=[enums.RouteTag.SHEETS])
user_router = APIRouter(prefix="/users", tags=[enums.RouteTag.USERS])


@router.post(
    "/order",
    response_model=schemas.OrderReadSystem | schemas.PreOrderReadSystem,
)
async def fetch_order_from_sheets(
    data: models.SheetEntity,
    user: models.User = Depends(auth_flows.current_active_superuser_api),
    session=Depends(db.get_async_session),
):
    model = await flows.get_order_from_sheets(session, data, user)
    if model.shop_order_id:
        return await orders_flows.create(session, models.OrderCreate.model_validate(model.model_dump()))
    else:
        return await preorder_flows.create(session, schemas.PreOrderCreate.model_validate(model.model_dump()))


@router.put(
    "/order",
    response_model=schemas.OrderReadSystem | schemas.PreOrderReadSystem,
)
async def update_order_from_sheets(
    data: models.SheetEntity,
    user: models.User = Depends(auth_flows.current_active_superuser_api),
    session=Depends(db.get_async_session),
):
    model = await flows.get_order_from_sheets(session, data, user)
    if model.shop_order_id:
        order = await orders_flows.get_by_order_id(session, model.order_id)
        return await orders_service.update(session, order, models.OrderUpdate.model_validate(model.model_dump()))
    else:
        preorder = await preorder_flows.get_by_order_id(session, model.order_id)
        return await preorder_service.update(
            session,
            preorder,
            schemas.PreOrderUpdate.model_validate(model.model_dump()),
        )


@router.patch(
    "/order",
    response_model=schemas.OrderReadSystem | schemas.PreOrderReadSystem,
)
async def patch_order_from_sheets(
    data: models.SheetEntity,
    user: models.User = Depends(auth_flows.current_active_superuser_api),
    session=Depends(db.get_async_session),
):
    model = await flows.get_order_from_sheets(session, data, user)
    if model.shop_order_id:
        order = await orders_flows.get_by_order_id(session, model.order_id)
        return await orders_service.update(
            session,
            order,
            models.OrderUpdate.model_validate(model.model_dump()),
            patch=True,
        )
    else:
        preorder = await preorder_flows.get_by_order_id(session, model.order_id)
        return await preorder_service.update(
            session, preorder, schemas.PreOrderUpdate.model_validate(model.model_dump()), patch=True
        )


@router.delete(
    "/order",
    response_model=schemas.OrderReadSystem | schemas.PreOrderReadSystem,
)
async def delete_order_from_sheets(
    data: models.SheetEntity,
    user: models.User = Depends(auth_flows.current_active_superuser_api),
    session=Depends(db.get_async_session),
):
    model = await flows.get_order_from_sheets(session, data, user)
    if model.shop_order_id:
        order = await orders_flows.get_by_order_id(session, model.order_id)
        return await orders_service.delete(session, order.id)
    else:
        preorder = await preorder_flows.get_by_order_id(session, model.order_id)
        return await preorder_service.delete(session, preorder.id)


@router.get("/parser/filter", response_model=pagination.Paginated[models.OrderSheetParseRead])
async def filter_google_sheets_parser(
    params: pagination.PaginationParams = Depends(),
    spreadsheet: str | None = None,
    _: models.User = Depends(auth_flows.current_active_superuser),
    session: AsyncSession = Depends(db.get_async_session),
):
    query = params.apply_pagination(sa.select(models.OrderSheetParse))
    if spreadsheet:
        query = query.where(models.OrderSheetParse.spreadsheet == spreadsheet)
    result = await session.execute(query)
    return pagination.Paginated(
        page=params.page,
        per_page=params.per_page,
        total=(await session.execute(sa.select(count(models.OrderSheetParse.id)))).one()[0],
        results=[models.OrderSheetParseRead.model_validate(parse) for parse in result.scalars()],
    )


@router.get("/parser", response_model=models.OrderSheetParseRead)
async def read_google_sheets_parser(
    spreadsheet: str,
    sheet_id: int,
    _: models.User = Depends(auth_flows.current_active_superuser),
    session=Depends(db.get_async_session),
):
    return await flows.get_by_spreadsheet_sheet(session, spreadsheet, sheet_id)


@router.post("/parser", response_model=models.OrderSheetParseRead)
async def create_google_sheets_parser(
    model: models.OrderSheetParseCreate,
    _: models.User = Depends(auth_flows.current_active_superuser),
    session=Depends(db.get_async_session),
):
    return await flows.create(session, model)


@router.delete("/parser")
async def delete_google_sheets_parser(
    spreadsheet: str,
    sheet_id: int,
    _: models.User = Depends(auth_flows.current_active_superuser),
    session=Depends(db.get_async_session),
):
    return await flows.delete(session, spreadsheet, sheet_id)


@router.put("/parser", response_model=models.OrderSheetParseRead)
async def update_google_sheets_parser(
    spreadsheet: str,
    sheet_id: int,
    data: models.OrderSheetParseUpdate,
    _: models.User = Depends(auth_flows.current_active_superuser),
    session=Depends(db.get_async_session),
):
    return await flows.update(session, spreadsheet, sheet_id, data)


@router.patch("/parser", response_model=models.OrderSheetParseRead)
async def patch_google_sheets_parser(
    spreadsheet: str,
    sheet_id: int,
    data: models.OrderSheetParseUpdate,
    _: models.User = Depends(auth_flows.current_active_superuser),
    session=Depends(db.get_async_session),
):
    return await flows.update(session, spreadsheet, sheet_id, data, patch=True)


@router.post("/report", response_model=schemas.AccountingReport)
async def generate_payment_report(
    data: schemas.AccountingReportSheetsForm,
    _: models.User = Depends(auth_flows.current_active_superuser_api),
    session=Depends(db.get_async_session),
):
    return await accounting_flows.create_report(
        session,
        data.start_date,
        data.end_date,
        data.first_sort,
        data.second_sort,
        data.spreadsheet,
        data.sheet_id,
        data.username,
        data.is_completed,
        data.is_paid,
    )


@user_router.post("/@me/google-token", status_code=201, response_model=models.AdminGoogleToken)
async def add_google_token(
    file: UploadFile,
    user=Depends(auth_flows.current_active_superuser),
    session=Depends(db.get_async_session),
):
    token = models.AdminGoogleToken.model_validate_json(await file.read())
    await service.create_token(session, user, token)
    return token


@user_router.get("/@me/google-token", response_model=models.AdminGoogleToken)
async def read_google_token(
    user=Depends(auth_flows.current_active_superuser),
    session=Depends(db.get_async_session),
):
    token = await service.get_token(session, user)
    if token is None:
        raise errors.ApiHTTPException(
            status_code=404,
            detail=[errors.ApiException(msg="Google Service account doesn't setup.", code="not_exist")],
        )
    return models.AdminGoogleToken.model_validate(token.token)


@router.post("/message/order", response_model=schemas.MessageCallback)
async def create_order_message(data: schemas.CreateOrderSheetMessage, session=Depends(db.get_async_session)):
    if data.is_preorder:
        preorder = await preorder_flows.get_by_order_id(session, data.order_id)
        preorder_read = await preorder_flows.format_preorder_system(session, preorder)
        resp = await message_service.create_order_message(
            session,
            preorder_read,
            schemas.CreateOrderMessage(
                integration=data.integration,
                order_id=preorder_read.id,
                is_preorder=data.is_preorder,
                categories=data.categories,
                configs=data.configs,
            ),
        )
        notifications_flows.send_sent_order_notify(preorder_read.order_id, resp)
    else:
        order = await order_flows.get_by_order_id(session, data.order_id)
        order_read = await order_flows.format_order_system(session, order)
        resp = await message_service.create_order_message(
            session,
            order_read,
            schemas.CreateOrderMessage(
                integration=data.integration,
                order_id=order_read.id,
                is_preorder=data.is_preorder,
                categories=data.categories,
                configs=data.configs,
            ),
        )
        notifications_flows.send_sent_order_notify(order_read.order_id, resp)

    return resp


@router.delete("/message/order", response_model=schemas.MessageCallback)
async def delete_order_message(data: schemas.DeleteOrderSheetMessage, session=Depends(db.get_async_session)):
    if data.is_preorder:
        preorder = await preorder_flows.get_by_order_id(session, data.order_id)
        resp = await message_service.delete_order_message(
            session,
            schemas.DeleteOrderMessage(
                integration=data.integration,
                order_id=preorder.id,
            ),
        )
        notifications_flows.send_deleted_order_notify(preorder.order_id, resp)
    else:
        order = await order_flows.get_by_order_id(session, data.order_id)
        resp = await message_service.delete_order_message(
            session,
            schemas.DeleteOrderMessage(
                integration=data.integration,
                order_id=order.id,
            ),
        )
        notifications_flows.send_deleted_order_notify(order.order_id, resp)
    return resp


@router.patch("/message/order", response_model=schemas.MessageCallback)
async def update_order_message(data: schemas.UpdateOrderSheetMessage, session=Depends(db.get_async_session)):
    if data.is_preorder:
        preorder = await preorder_flows.get_by_order_id(session, data.order_id)
        preorder_read = await preorder_flows.format_preorder_system(session, preorder)
        resp = await message_service.update_order_message(
            session,
            preorder_read,
            schemas.UpdateOrderMessage(
                integration=data.integration,
                order_id=preorder_read.id,
                is_preorder=data.is_preorder,
                configs=data.configs,
            ),
        )
        notifications_flows.send_edited_order_notify(preorder.order_id, resp)
    else:
        order = await order_flows.get_by_order_id(session, data.order_id)
        order_read = await order_flows.format_order_system(session, order)
        resp = await message_service.update_order_message(
            session,
            order_read,
            schemas.UpdateOrderMessage(
                integration=data.integration,
                order_id=order_read.id,
                is_preorder=data.is_preorder,
                configs=data.configs,
            ),
        )
        notifications_flows.send_edited_order_notify(order.order_id, resp)
    return resp
