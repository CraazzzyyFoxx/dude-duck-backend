import datetime

from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, HTTPException
from lxml.builder import ElementMaker
from lxml.etree import tostring
from starlette import status
from starlette.responses import Response

from app.core import enums
from app.services.accounting import flows as accounting_flows
from app.services.accounting import models as accounting_models
from app.services.auth import flows as auth_flows
from app.services.auth import models as auth_models
from app.services.currency import flows as currency_flows
from app.services.orders import flows as orders_flows
from app.services.orders import schemas as orders_schemas
from app.services.orders import service as orders_service
from app.services.preorders import flows as preorders_flows
from app.services.preorders import models as preorders_schemes
from app.services.search import models as search_models
from app.services.search import service as search_service

from . import flows, models

router = APIRouter(prefix='/sheets', tags=[enums.RouteTag.SHEETS])


@router.get('/currency')
async def get_currency_for_sheet(date: datetime.date):
    e_maker = ElementMaker()
    wallet = await currency_flows.get(datetime.datetime(year=date.year, month=date.month, day=date.day))
    wallet_str = str(wallet.quotes["RUB"]).replace(".", ",")
    the_doc = e_maker.root(e_maker.USD(wallet_str))
    return Response(content=tostring(the_doc, pretty_print=True), media_type="text/xml")


@router.post('/orders', response_model=orders_schemas.OrderReadSystem | preorders_schemes.PreOrderReadSystem)
async def fetch_order_from_sheets(
        data: models.SheetEntity,
        user: auth_models.User = Depends(auth_flows.current_active_superuser_api)
):

    model = await flows.get_order_from_sheets(data, user)
    if model.shop_order_id:
        return await orders_flows.create(model)
    else:
        return await preorders_flows.create(model)


@router.patch('/orders', response_model=orders_schemas.OrderReadSystem | preorders_schemes.PreOrderReadSystem)
async def update_order_from_sheets(
        data: models.SheetEntity,
        user: auth_models.User = Depends(auth_flows.current_active_superuser_api)
):
    model = await flows.get_order_from_sheets(data, user)
    if not model.shop_order_id:
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                             detail=[{"msg": "The preorder cannot be updated."}])
    order = await orders_flows.get_by_order_id(model.order_id)
    return await orders_service.update(order, model)


@router.patch('/orders/{order_id}', response_model=list[accounting_models.UserOrderRead])
async def patch_boosters(
        order_id: PydanticObjectId | str,
        model: accounting_models.SheetUserOrderCreate,
        by_sheets: bool = False,
        _=Depends(auth_flows.current_active_superuser_api)
):
    if by_sheets:
        order = await orders_flows.get_by_order_id(order_id)
    else:
        order = await orders_flows.get(order_id)
    data = await accounting_flows.update_boosters_percent(order, model)
    return data


@router.get('/parser', response_model=search_models.Paginated[models.OrderSheetParseRead])
async def reads_google_sheets_parser(
        paging: search_models.PaginationParams = Depends(),
        sorting: search_models.SortingParams = Depends(),
        _: auth_models.User = Depends(auth_flows.current_active_superuser)
):
    return await search_service.paginate(models.OrderSheetParse.find({}), paging, sorting)


@router.get('/parser/{spreadsheet}/{sheet_id}', response_model=models.OrderSheetParseRead)
async def read_google_sheets_parser(
        spreadsheet: str,
        sheet_id: int,
        _: auth_models.User = Depends(auth_flows.current_active_superuser)
):
    return await flows.get_by_spreadsheet_sheet(spreadsheet, sheet_id)


@router.post('/parser', response_model=models.OrderSheetParseRead)
async def create_google_sheets_parser(
        model: models.OrderSheetParseCreate,
        _: auth_models.User = Depends(auth_flows.current_active_superuser)
):
    return await flows.create(model)


@router.delete('/parser/{spreadsheet}/{sheet_id}')
async def delete_google_sheets_parser(
        spreadsheet: str,
        sheet_id: int,
        _: auth_models.User = Depends(auth_flows.current_active_superuser)
):
    return await flows.delete(spreadsheet, sheet_id)


@router.patch('/parser/{spreadsheet}/{sheet_id}', response_model=models.OrderSheetParseRead)
async def update_google_sheets_parser(
        spreadsheet: str,
        sheet_id: int,
        data: models.OrderSheetParseUpdate,
        _: auth_models.User = Depends(auth_flows.current_active_superuser)
):
    return await flows.update(spreadsheet, sheet_id, data)
