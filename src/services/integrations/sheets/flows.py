from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from src.core import errors
from src.services.auth import models as auth_models
from src.services.order import models as order_models
from src.services.order import schemas as order_schemas
from src.services.tasks import service as tasks_service

from . import models, service


async def get(session: AsyncSession, parser_id: int):
    parser = await service.get(session, parser_id)
    if not parser:
        raise errors.ApiHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[errors.ApiException(msg="A Spreadsheet parse with this id does not exist.", code="not_exist")],
        )
    return parser


async def get_by_spreadsheet_sheet(session: AsyncSession, spreadsheet: str, sheet: int):
    parser = await service.get_by_spreadsheet_sheet(session, spreadsheet, sheet)
    if not parser:
        raise errors.ApiHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[
                errors.ApiException(
                    msg="A Spreadsheet parse with this spreadsheet and sheet_id does not exist.", code="not_exist"
                )
            ],
        )
    return parser


async def get_by_spreadsheet_sheet_read(session: AsyncSession, spreadsheet: str, sheet: int):
    parser = await service.get_by_spreadsheet_sheet_read(session, spreadsheet, sheet)
    if not parser:
        raise errors.ApiHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[
                errors.ApiException(
                    msg="A Spreadsheet parse with this spreadsheet and sheet_id does not exist.", code="not_exist"
                )
            ],
        )
    return parser


async def create(session: AsyncSession, parser_in: models.OrderSheetParseCreate):
    data = await service.get_by_spreadsheet_sheet_read(session, parser_in.spreadsheet, parser_in.sheet_id)
    if data:
        raise errors.ApiHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[errors.ApiException(msg="A Spreadsheet parse with this id already exists", code="already_exist")],
        )
    return await service.create(session, parser_in)


async def update(session: AsyncSession, spreadsheet, sheet_id, parser_in: models.OrderSheetParseUpdate):
    data = await get_by_spreadsheet_sheet(session, spreadsheet, sheet_id)
    return await service.update(session, data, parser_in)


async def delete(session: AsyncSession, spreadsheet: str, sheet_id: int):
    parser = await get_by_spreadsheet_sheet(session, spreadsheet, sheet_id)
    return await service.delete(session, parser.id)


async def get_order_from_sheets(session: AsyncSession, data: models.SheetEntity, user: auth_models.User):
    if not user.google:
        raise errors.ApiHTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=[errors.ApiException(msg="Google Service account doesn't setup.", code="not_exist")],
        )
    parser = await get_by_spreadsheet_sheet_read(session, data.spreadsheet, data.sheet_id)
    try:
        model = service.get_row_data(
            models.OrderReadSheets,
            user.google,
            parser,
            data.row_id,
        )
    except ValidationError as error:
        raise errors.GoogleSheetsParserError.http_exception(
            models.OrderReadSheets, data.spreadsheet, data.sheet_id, data.row_id, error
        ) from error
    return model


async def order_to_sheets(session: AsyncSession, order: order_models.Order, order_in: order_schemas.OrderReadSystem):
    parser = await get_by_spreadsheet_sheet_read(session, order.spreadsheet, order.sheet_id)
    if parser is not None:
        tasks_service.update_order.delay(parser.model_dump(mode="json"), order.row_id, order_in.model_dump(mode="json"))
