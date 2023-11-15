import datetime

import sqlalchemy as sa

from fastapi import APIRouter, Depends
from lxml.builder import ElementMaker, E
from lxml.etree import tostring
from sqlalchemy.sql.functions import count
from starlette.responses import Response

from src.core import enums, db, pagination
from src.services.accounting import flows as accounting_flows
from src.services.accounting import models as accounting_models
from src.services.auth import flows as auth_flows
from src.services.auth import models as auth_models
from src.services.currency import flows as currency_flows
from src.services.order import flows as orders_flows
from src.services.order import models as order_models
from src.services.order import schemas as orders_schemas
from src.services.order import service as orders_service
from src.services.preorder import flows as preorders_flows
from src.services.preorder import models as preorder_models
from src.services.preorder import models as preorders_schemes
from src.services.preorder import service as preorder_service

from . import flows, models

router = APIRouter(prefix="/sheets", tags=[enums.RouteTag.SHEETS])


@router.get("/currency")
async def get_currency_wow_for_sheet(date: datetime.date, session=Depends(db.get_async_session)):
    e_maker = ElementMaker()
    wallet = await currency_flows.get(session, datetime.datetime(year=date.year, month=date.month, day=date.day))
    the_doc = e_maker.root()
    for key, value in wallet.quotes.items():
        the_doc.append(E(key, str(value).replace(".", ",")))  # noqa
    return Response(content=tostring(the_doc, pretty_print=True), media_type="text/xml")


@router.post("/orders", response_model=orders_schemas.OrderReadSystem | preorders_schemes.PreOrderReadSystem)
async def fetch_order_from_sheets(
    data: models.SheetEntity,
    user: auth_models.User = Depends(auth_flows.current_active_superuser_api),
    session=Depends(db.get_async_session),
):
    model = await flows.get_order_from_sheets(session, data, user)
    if model.shop_order_id:
        return await orders_flows.create(session, order_models.OrderCreate.model_validate(model.model_dump()))
    else:
        return await preorders_flows.create(session, preorder_models.PreOrderCreate.model_validate(model.model_dump()))


@router.put("/orders", response_model=orders_schemas.OrderReadSystem | preorders_schemes.PreOrderReadSystem)
async def update_order_from_sheets(
    data: models.SheetEntity,
    user: auth_models.User = Depends(auth_flows.current_active_superuser_api),
    session=Depends(db.get_async_session),
):
    model = await flows.get_order_from_sheets(session, data, user)
    if model.shop_order_id:
        order = await orders_flows.get_by_order_id(session, model.order_id)
        return await orders_service.update(session, order, order_models.OrderUpdate.model_validate(model.model_dump()))
    else:
        preorder = await preorders_flows.get_by_order_id(session, model.order_id)
        return await preorder_service.update(
            session, preorder, preorder_models.PreOrderUpdate.model_validate(model.model_dump())
        )


@router.patch("/orders", response_model=orders_schemas.OrderReadSystem | preorders_schemes.PreOrderReadSystem)
async def patch_order_from_sheets(
    data: models.SheetEntity,
    user: auth_models.User = Depends(auth_flows.current_active_superuser_api),
    session=Depends(db.get_async_session),
):
    model = await flows.get_order_from_sheets(session, data, user)
    if model.shop_order_id:
        order = await orders_flows.get_by_order_id(session, model.order_id)
        return await orders_service.patch(session, order, order_models.OrderUpdate.model_validate(model.model_dump()))
    else:
        preorder = await preorders_flows.get_by_order_id(session, model.order_id)
        return await preorder_service.patch(
            session, preorder, preorder_models.PreOrderUpdate.model_validate(model.model_dump())
        )


@router.delete("/orders", response_model=orders_schemas.OrderReadSystem | preorders_schemes.PreOrderReadSystem)
async def delete_order_from_sheets(
    data: models.SheetEntity,
    user: auth_models.User = Depends(auth_flows.current_active_superuser_api),
    session=Depends(db.get_async_session),
):
    model = await flows.get_order_from_sheets(session, data, user)
    if model.shop_order_id:
        order = await orders_flows.get_by_order_id(session, model.order_id)
        return await orders_service.delete(session, order.id)
    else:
        preorder = await preorders_flows.get_by_order_id(session, model.order_id)
        return await preorder_service.delete(session, preorder.id)


@router.get("/parser", response_model=pagination.Paginated[models.OrderSheetParseRead])
async def reads_google_sheets_parser(
    params: pagination.PaginationParams = Depends(),
    _: auth_models.User = Depends(auth_flows.current_active_superuser),
    session: db.AsyncSession = Depends(db.get_async_session),
):
    query = sa.select(models.OrderSheetParse).offset(params.offset).limit(params.limit).order_by(params.order_by)
    result = await session.execute(query)
    results = [models.OrderSheetParseRead.model_validate(parse) for parse in result.scalars()]
    total = await session.execute(sa.select(count(models.OrderSheetParse.id)))
    return pagination.Paginated(page=params.page, per_page=params.per_page, total=total.first()[0], results=results)


@router.get("/parser", response_model=models.OrderSheetParseRead)
async def read_google_sheets_parser(
    spreadsheet: str,
    sheet_id: int,
    _: auth_models.User = Depends(auth_flows.current_active_superuser),
    session=Depends(db.get_async_session),
):
    return await flows.get_by_spreadsheet_sheet(session, spreadsheet, sheet_id)


@router.post("/parser", response_model=models.OrderSheetParseRead)
async def create_google_sheets_parser(
    model: models.OrderSheetParseCreate,
    _: auth_models.User = Depends(auth_flows.current_active_superuser),
    session=Depends(db.get_async_session),
):
    return await flows.create(session, model)


@router.delete("/parser")
async def delete_google_sheets_parser(
    spreadsheet: str,
    sheet_id: int,
    _: auth_models.User = Depends(auth_flows.current_active_superuser),
    session=Depends(db.get_async_session),
):
    return await flows.delete(session, spreadsheet, sheet_id)


@router.patch("/parser", response_model=models.OrderSheetParseRead)
async def update_google_sheets_parser(
    spreadsheet: str,
    sheet_id: int,
    data: models.OrderSheetParseUpdate,
    _: auth_models.User = Depends(auth_flows.current_active_superuser),
    session=Depends(db.get_async_session),
):
    return await flows.update(session, spreadsheet, sheet_id, data)


@router.post("/report", response_model=accounting_models.AccountingReport)
async def generate_payment_report(
    data: accounting_models.AccountingReportSheetsForm,
    _: auth_models.User = Depends(auth_flows.current_active_superuser_api),
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
