from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from src import models, schemas
from src.core import errors
from src.services.integrations.notifications import flows as notifications_flows
from src.services.payroll import service as payroll_service
from src.services.tasks import service as tasks_service

from . import service


async def get(session: AsyncSession, parser_id: int):
    parser = await service.get(session, parser_id)
    if not parser:
        raise errors.ApiHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[
                errors.ApiException(
                    msg="A Spreadsheet parse with this id does not exist.",
                    code="not_exist",
                )
            ],
        )
    return parser


async def get_by_spreadsheet_sheet(session: AsyncSession, spreadsheet: str, sheet: int):
    parser = await service.get_by_spreadsheet_sheet(session, spreadsheet, sheet)
    if not parser:
        raise errors.ApiHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[
                errors.ApiException(
                    msg="A Spreadsheet parse with this spreadsheet and sheet_id does not exist.",
                    code="not_exist",
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
                    msg="A Spreadsheet parse with this spreadsheet and sheet_id does not exist.",
                    code="not_exist",
                )
            ],
        )
    return parser


async def create(session: AsyncSession, parser_in: models.OrderSheetParseCreate):
    data = await service.get_by_spreadsheet_sheet_read(session, parser_in.spreadsheet, parser_in.sheet_id)
    if data:
        raise errors.ApiHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[
                errors.ApiException(
                    msg="A Spreadsheet parse with this id already exists",
                    code="already_exist",
                )
            ],
        )
    return await service.create(session, parser_in)


async def update(
    session: AsyncSession, spreadsheet, sheet_id, parser_in: models.OrderSheetParseUpdate, patch: bool = False
):
    data = await get_by_spreadsheet_sheet(session, spreadsheet, sheet_id)
    return await service.update(session, data, parser_in, patch=patch)


async def delete(session: AsyncSession, spreadsheet: str, sheet_id: int):
    parser = await get_by_spreadsheet_sheet(session, spreadsheet, sheet_id)
    return await service.delete(session, parser.id)


async def get_order_from_sheets(session: AsyncSession, data: models.SheetEntity, user: models.User):
    token = await service.get_token(session, user)
    if not token:
        raise errors.ApiHTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=[errors.ApiException(msg="Google Service account doesn't setup.", code="not_exist")],
        )
    parser = await get_by_spreadsheet_sheet_read(session, data.spreadsheet, data.sheet_id)
    try:
        model = service.get_row_data(
            models.OrderReadSheets,
            token.token,
            parser,
            data.row_id,
        )
    except ValidationError as error:
        raise errors.GoogleSheetsParserError.http_exception(
            models.OrderReadSheets, data.spreadsheet, data.sheet_id, data.row_id, error
        ) from error
    return model


async def order_to_sheets(
    session: AsyncSession,
    order: models.Order,
    order_in: schemas.OrderReadSystem,
):
    parser = await get_by_spreadsheet_sheet_read(session, order.spreadsheet, order.sheet_id)
    if parser is not None:
        tasks_service.update_order.delay(
            parser.model_dump(mode="json"),
            order.row_id,
            order_in.model_dump(mode="json"),
        )


def convert_user_to_sheets(user: models.UserReadWithAccountsAndPayrolls) -> models.CreateUpdateUserSheets:
    model = models.CreateUpdateUserSheets(
        id=user.id,
        name=user.name,
        email=user.email,
        max_orders=user.max_orders,
        is_verified=user.is_verified,
        is_verified_email=user.is_verified_email,
    )
    for payroll in user.payrolls:
        if payroll.type == models.PayrollType.binance_email:
            model.binance_email = payroll.value
        elif payroll.type == models.PayrollType.binance_id:
            model.binance_id = payroll.value
        elif payroll.type == models.PayrollType.trc20:
            model.trc20 = payroll.value
        elif payroll.type == models.PayrollType.phone:
            model.phone = payroll.value
            model.bank = payroll.bank
        elif payroll.type == models.PayrollType.card:
            model.bankcard = payroll.value
            model.bank = payroll.bank
    if user.telegram is not None:
        model.telegram = user.telegram.username
    return model


async def create_or_update_user(
    session: AsyncSession,
    user: models.User,
) -> models.UserReadWithAccountsAndPayrolls:
    payrolls = await payroll_service.get_by_user_id(session, user.id)
    user_with_accounts = await notifications_flows.get_user_accounts(
        session, models.UserRead.model_validate(user, from_attributes=True)
    )
    user_read = models.UserReadWithAccountsAndPayrolls(
        **user_with_accounts.model_dump(),
        payrolls=[models.PayrollRead.model_validate(p, from_attributes=True) for p in payrolls],
    )
    parser = await service.get_default_booster_read(session)
    if parser is not None:
        tasks_service.create_or_update_booster.delay(
            parser.model_dump(mode="json"),
            user.id,
            convert_user_to_sheets(user_read).model_dump(mode="json"),
        )
    return user_read
