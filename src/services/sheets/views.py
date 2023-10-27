import datetime

from fastapi import APIRouter, Depends
from lxml.builder import ElementMaker
from lxml.etree import tostring
from starlette.responses import Response

from src.core import enums, db
from src.services.accounting import flows as accounting_flows
from src.services.accounting import models as accounting_models
from src.services.auth import flows as auth_flows
from src.services.auth import models as auth_models
from src.services.currency import flows as currency_flows
from src.services.orders import flows as orders_flows
from src.services.orders import models as order_models
from src.services.orders import schemas as orders_schemas
from src.services.orders import service as orders_service
from src.services.preorders import flows as preorders_flows
from src.services.preorders import models as preorder_models
from src.services.preorders import models as preorders_schemes
from src.services.preorders import service as preorder_service
from src.services.search import models as search_models
from src.services.search import service as search_service

from . import flows, models

router = APIRouter(prefix="/sheets", tags=[enums.RouteTag.SHEETS])


@router.get("/currency/rub")
async def get_currency_rub_for_sheet(date: datetime.date, session=Depends(db.get_async_session)):
    e_maker = ElementMaker()
    wallet = await currency_flows.get(session, datetime.datetime(year=date.year, month=date.month, day=date.day))
    wallet_str = str(wallet.quotes["RUB"]).replace(".", ",")
    the_doc = e_maker.root(e_maker.RUB(wallet_str))
    return Response(content=tostring(the_doc, pretty_print=True), media_type="text/xml")


@router.get("/currency/wow")
async def get_currency_wow_for_sheet(date: datetime.date, session=Depends(db.get_async_session)):
    e_maker = ElementMaker()
    wallet = await currency_flows.get(session, datetime.datetime(year=date.year, month=date.month, day=date.day))
    wallet_str = str(wallet.quotes["WOW"]).replace(".", ",")
    the_doc = e_maker.root(e_maker.WOW(wallet_str))
    return Response(content=tostring(the_doc, pretty_print=True), media_type="text/xml")


@router.post("/orders", response_model=orders_schemas.OrderReadSystem | preorders_schemes.PreOrderReadSystem)
async def fetch_order_from_sheets(
    data: models.SheetEntity,
    user: auth_models.User = Depends(auth_flows.current_active_superuser_api),
    session=Depends(db.get_async_session)
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
    session=Depends(db.get_async_session)
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
    session=Depends(db.get_async_session)
):
    model = await flows.get_order_from_sheets(session, data, user)
    if model.shop_order_id:
        order = await orders_flows.get_by_order_id(session, model.order_id)
        return await orders_service.patch(session, order, order_models.OrderUpdate.model_validate(model.model_dump()))
    else:
        preorder = await preorders_flows.get_by_order_id(session, model.order_id)
        return await preorder_service.patch(
            session, preorder, preorder_models.PreOrderUpdate.model_validate(model.model_dump()))


@router.delete("/orders", response_model=orders_schemas.OrderReadSystem | preorders_schemes.PreOrderReadSystem)
async def delete_order_from_sheets(
    data: models.SheetEntity,
    user: auth_models.User = Depends(auth_flows.current_active_superuser_api),
    session=Depends(db.get_async_session)
):
    model = await flows.get_order_from_sheets(session, data, user)
    if model.shop_order_id:
        order = await orders_flows.get_by_order_id(session, model.order_id)
        return await orders_service.delete(session, order.id)
    else:
        preorder = await preorders_flows.get_by_order_id(session, model.order_id)
        return await preorder_service.delete(session, preorder.id)


@router.get("/parser", response_model=search_models.Paginated[models.OrderSheetParseRead])
async def reads_google_sheets_parser(
    paging: search_models.PaginationParams = Depends(),
    sorting: search_models.SortingParams = Depends(),
    _: auth_models.User = Depends(auth_flows.current_active_superuser),
):
    return await search_service.paginate(models.OrderSheetParse.filter(), paging, sorting)


@router.get("/parser/{spreadsheet}/{sheet_id}", response_model=models.OrderSheetParseRead)
async def read_google_sheets_parser(
    spreadsheet: str,
    sheet_id: int,
    _: auth_models.User = Depends(auth_flows.current_active_superuser),
    session=Depends(db.get_async_session)
):
    return await flows.get_by_spreadsheet_sheet(session, spreadsheet, sheet_id)


@router.post("/parser", response_model=models.OrderSheetParseRead)
async def create_google_sheets_parser(
    model: models.OrderSheetParseCreate,
    _: auth_models.User = Depends(auth_flows.current_active_superuser),
    session=Depends(db.get_async_session)
):
    return await flows.create(session, model)


@router.delete("/parser/{spreadsheet}/{sheet_id}")
async def delete_google_sheets_parser(
    spreadsheet: str,
    sheet_id: int,
    _: auth_models.User = Depends(auth_flows.current_active_superuser),
    session=Depends(db.get_async_session)
):
    return await flows.delete(session, spreadsheet, sheet_id)


@router.patch("/parser/{spreadsheet}/{sheet_id}", response_model=models.OrderSheetParseRead)
async def update_google_sheets_parser(
    spreadsheet: str,
    sheet_id: int,
    data: models.OrderSheetParseUpdate,
    _: auth_models.User = Depends(auth_flows.current_active_superuser),
    session=Depends(db.get_async_session)
):
    return await flows.update(session, spreadsheet, sheet_id, data)


@router.post("/report", response_model=accounting_models.AccountingReport)
async def generate_payment_report(
    data: accounting_models.AccountingReportSheetsForm,
    _: auth_models.User = Depends(auth_flows.current_active_superuser_api),
    session=Depends(db.get_async_session)
):
    return await accounting_flows.create_report(
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
