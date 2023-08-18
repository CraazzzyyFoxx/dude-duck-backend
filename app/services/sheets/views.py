from fastapi import APIRouter, Depends, HTTPException
from starlette import status

from app.core import enums
from app.services.auth import service as auth_service
from app.services.orders import service as orders_service
from app.services.orders import flows as orders_flows
from app.services.search import service as search_service

from . import models, flows

router = APIRouter(prefix='/sheets', tags=[enums.RouteTag.SHEETS])


# @router.post('/order-move', status_code=status.HTTP_200_OK, response_model=Order)
# async def sheets_order_move(order: SheetEntity, user: User = Depends(current_active_superuser)):
#     if not user.google:
#         raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Google Service account don't setup")
#
#     model_pyd = await GoogleSheetsServiceManager.get(user=user).get_order(
#         order.spreadsheet,
#         order.sheet_id,
#         order.row,
#         apply_model=False
#     )
#
#     model = await GoogleSheetsServiceManager.get(user=user).create_order("M+", 0, model_pyd)
#     return await model.create()


@router.post('/order', status_code=status.HTTP_200_OK, response_model=orders_service.models.Order)
async def fetch_order_from_sheets(
        data: models.SheetEntity,
        user: auth_service.models.User = Depends(auth_service.current_active_superuser_api)
):
    model = await flows.get_order_from_sheets(data, user)
    return await orders_flows.create(model)


@router.patch('/order', status_code=status.HTTP_200_OK, response_model=orders_service.models.Order)
async def update_order_from_sheets(
        data: models.SheetEntity,
        user: auth_service.models.User = Depends(auth_service.current_active_superuser_api)
):
    model = await flows.get_order_from_sheets(data, user)
    order = await orders_flows.get_by_order_id(model.order_id)
    return await orders_service.update(order, model)


@router.get('', response_model=search_service.models.Paginated[models.OrderSheetParse])
async def reads_google_sheets_parser(
        paging: search_service.models.PaginationParams = Depends(),
        sorting: search_service.models.SortingParams = Depends(),
        _: auth_service.models.User = Depends(auth_service.current_active_superuser)
):
    return await search_service.paginate(models.OrderSheetParse.find({}), paging, sorting)


@router.get('/{spreadsheet}/{sheet_id}', response_model=models.OrderSheetParse)
async def read_google_sheets_parser(
        spreadsheet: str,
        sheet_id: int,
        _: auth_service.models.User = Depends(auth_service.current_active_superuser)
):
    model = await models.OrderSheetParse.get_spreadsheet_sheet(spreadsheet, sheet_id)
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[{"msg": "A Spreadsheet parse with this id does not exist."}],
        )
    return model


@router.post('', response_model=models.OrderSheetParse)
async def create_google_sheets_parser(
        model: models.OrderSheetParseCreate,
        _: auth_service.models.User = Depends(auth_service.current_active_superuser)
):
    data = await models.OrderSheetParse.get_spreadsheet_sheet(model.spreadsheet, model.sheet_id)

    if data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[{"msg": "A Spreadsheet parse with this id already exists"}],
        )
    parser = models.OrderSheetParse.model_validate(model.model_dump())
    d = await parser.create()
    return d


@router.delete('/{spreadsheet}/{sheet_id}', response_model=models.OrderSheetParse)
async def delete_google_sheets_parser(
        spreadsheet: str,
        sheet_id: int,
        _: auth_service.models.User = Depends(auth_service.current_active_superuser)
):
    model = await models.OrderSheetParse.get_spreadsheet_sheet(spreadsheet, sheet_id)

    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[{"msg": "A Spreadsheet parse with this id does not exist."}],
        )
    await model.delete()
    return model


@router.patch('/{spreadsheet}/{sheet_id}', response_model=models.OrderSheetParse)
async def update_google_sheets_parser(
        spreadsheet: str,
        sheet_id: int,
        data: models.OrderSheetParseUpdate,
        _: auth_service.models.User = Depends(auth_service.current_active_superuser)
):
    model = await models.OrderSheetParse.get_spreadsheet_sheet(spreadsheet, sheet_id)

    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[{"msg": "A Spreadsheet parse with this id does not exist."}],
        )
    model.update_from(data)
    await model.save()
    return model
