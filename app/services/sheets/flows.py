from pydantic import ValidationError
from starlette import status

from app.core import errors
from app.services.auth import models as auth_models

from . import models, service


async def get(parser_id: int):
    parser = await service.get(parser_id)
    if not parser:
        raise errors.DDHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[errors.DDException(msg="A Spreadsheet parse with this id does not exist.", code="not_exist")],
        )
    return parser


async def get_by_spreadsheet_sheet(spreadsheet: str, sheet: int):
    parser = await service.get_by_spreadsheet_sheet(spreadsheet, sheet)
    if not parser:
        raise errors.DDHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[
                errors.DDException(
                    msg="A Spreadsheet parse with this spreadsheet and sheet_id does not exist.", code="not_exist"
                )
            ],
        )
    return parser


async def create(parser_in: models.OrderSheetParseCreate):
    data = await service.get_by_spreadsheet_sheet(parser_in.spreadsheet, parser_in.sheet_id)
    if data:
        raise errors.DDHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[
                errors.DDException(msg="A Spreadsheet parse with this id already exists", code="already_exist")
            ],
        )
    return await service.create(parser_in)


async def update(spreadsheet, sheet_id, parser_in: models.OrderSheetParseUpdate):
    data = await get_by_spreadsheet_sheet(spreadsheet, sheet_id)
    return await service.update(data, parser_in)


async def delete(spreadsheet: str, sheet_id: int):
    parser = await get_by_spreadsheet_sheet(spreadsheet, sheet_id)
    return await service.delete(parser.id)


async def get_order_from_sheets(data: models.SheetEntity, user: auth_models.User):
    if not user.google:
        raise errors.DDHTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=[errors.DDException(msg="Google Service account doesn't setup.", code="not_exist")],
        )
    parser = await get_by_spreadsheet_sheet(data.spreadsheet, data.sheet_id)
    try:
        model = service.get_row_data(
            models.OrderReadSheets,
            user.google,
            models.OrderSheetParseRead.model_validate(parser, from_attributes=True),
            data.row_id,
        )
    except ValidationError as error:
        raise errors.GoogleSheetsParserError.http_exception(
            models.OrderReadSheets, data.spreadsheet, data.sheet_id, data.row_id, error
        ) from error
    return model
