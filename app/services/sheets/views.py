from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, HTTPException
from starlette import status

from app.core import enums
from app.services.auth import flows as auth_flows
from app.services.orders import service as orders_service
from app.services.orders import flows as orders_flows
from app.services.orders import schemas as orders_schemas
from app.services.preorders import models as preorders_schemes
from app.services.preorders import flows as preorders_flows
from app.services.search import service as search_service
from app.services.accounting import flows as accounting_flows
from app.services.telegram.message import flows as message_flows

from . import models, flows

router = APIRouter(prefix='/sheets', tags=[enums.RouteTag.SHEETS])


@router.post('/orders', response_model=orders_schemas.OrderRead | preorders_schemes.PreOrderRead)
async def fetch_order_from_sheets(
        data: models.SheetEntity,
        user: auth_flows.models.User = Depends(auth_flows.current_active_superuser_api)
):
    model = await flows.get_order_from_sheets(data, user)
    if model.shop_order_id:
        return await orders_flows.create(model)
    else:
        return await preorders_flows.create(model)


@router.patch('/orders', response_model=orders_schemas.OrderRead | preorders_schemes.PreOrderRead)
async def update_order_from_sheets(
        data: models.SheetEntity,
        user: auth_flows.models.User = Depends(auth_flows.current_active_superuser_api)
):
    model = await flows.get_order_from_sheets(data, user)
    if not model.shop_order_id:
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                             detail=[{"msg": "The preorder cannot be updated."}])
    order = await orders_flows.get_by_order_id(model.order_id)
    return await orders_service.update(order, model)


@router.patch('/orders/{order_id}', response_model=list[accounting_flows.models.UserOrderRead])
async def patch_boosters(
        order_id: PydanticObjectId | str,
        model: accounting_flows.models.SheetUserOrderCreate,
        by_sheets: bool = False,
        _=Depends(auth_flows.current_active_superuser_api)
):
    if by_sheets:
        order = await orders_flows.get_by_order_id(order_id)
    else:
        order = await orders_flows.get(order_id)
    data = await accounting_flows.update_boosters_percent(order, model)
    return data


@router.get('', response_model=search_service.models.Paginated[models.OrderSheetParseRead])
async def reads_google_sheets_parser(
        paging: search_service.models.PaginationParams = Depends(),
        sorting: search_service.models.SortingParams = Depends(),
        _: auth_flows.models.User = Depends(auth_flows.current_active_superuser)
):
    return await search_service.paginate(models.OrderSheetParse.find({}), paging, sorting)


@router.get('/{spreadsheet}/{sheet_id}', response_model=models.OrderSheetParseRead)
async def read_google_sheets_parser(
        spreadsheet: str,
        sheet_id: int,
        _: auth_flows.models.User = Depends(auth_flows.current_active_superuser)
):
    return await flows.get_by_spreadsheet_sheet(spreadsheet, sheet_id)


@router.post('', response_model=models.OrderSheetParseRead)
async def create_google_sheets_parser(
        model: models.OrderSheetParseCreate,
        _: auth_flows.models.User = Depends(auth_flows.current_active_superuser)
):
    return await flows.create(model)


@router.delete('/{spreadsheet}/{sheet_id}')
async def delete_google_sheets_parser(
        spreadsheet: str,
        sheet_id: int,
        _: auth_flows.models.User = Depends(auth_flows.current_active_superuser)
):
    return await flows.delete(spreadsheet, sheet_id)


@router.patch('/{spreadsheet}/{sheet_id}', response_model=models.OrderSheetParseRead)
async def update_google_sheets_parser(
        spreadsheet: str,
        sheet_id: int,
        data: models.OrderSheetParseUpdate,
        _: auth_flows.models.User = Depends(auth_flows.current_active_superuser)
):
    return await flows.update(spreadsheet, sheet_id, data)
