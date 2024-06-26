import datetime
import time
import typing
from typing import Callable

import gspread
import sqlalchemy as sa
from fastapi.encoders import jsonable_encoder
from gspread.utils import DateTimeOption, ValueInputOption, ValueRenderOption, rowcol_to_a1
from loguru import logger
from pydantic import BaseModel, EmailStr, HttpUrl, SecretStr, ValidationError, create_model, field_validator
from pydantic._internal._model_construction import ModelMetaclass
from pydantic_extra_types.payment import PaymentCardNumber
from pydantic_extra_types.phone_numbers import PhoneNumber
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from src import models
from src.core import config, errors
from src.services.time import service as time_servie

type_map = {
    "int": int,
    "str": str,
    "float": float,
    "bool": bool,
    "timedelta": datetime.timedelta,
    "datetime": datetime.datetime,
    "SecretStr": SecretStr,
    "EmailStr": EmailStr,
    "HttpUrl": HttpUrl,
    "PhoneNumber": PhoneNumber,
    "PaymentCardNumber": PaymentCardNumber,
}

BM = typing.TypeVar("BM", bound=BaseModel)

_CACHE: dict = {}


def enum_parse(field, extra) -> Callable[[str], str]:
    def decorator(v: str) -> str:
        if v not in extra:
            raise ValueError(f"The {field} must be [{' | '.join(extra)}]")
        return v

    return decorator


def parse_datetime(v: str) -> typing.Any:
    if v is None:
        return None
    return time_servie.convert_time(v, conversion_mode=time_servie.ConversionMode.ABSOLUTE)


def parse_timedelta(v: str) -> typing.Any:
    if v is None:
        return None
    now = datetime.datetime.now(datetime.UTC)
    converted_time = time_servie.convert_time(v, now=now, conversion_mode=time_servie.ConversionMode.RELATIVE)
    return converted_time - now


def get_type(type_name: str, null: bool):
    if "|" in type_name:
        names = type_name.split("|")
        return get_type(names[0].strip(), False) | get_type(names[1].strip(), null)

    if null:
        return type_map[type_name] | None
    return type_map[type_name]


async def get(session: AsyncSession, parser_id: int) -> models.OrderSheetParse | None:
    result = await session.scalars(sa.select(models.OrderSheetParse).where(models.OrderSheetParse.id == parser_id))
    return result.first()


async def create(session: AsyncSession, parser_in: models.OrderSheetParseCreate):
    parser = models.OrderSheetParse(**parser_in.model_dump())
    session.add(parser)
    await session.commit()
    return parser


async def delete(session: AsyncSession, parser_id: int):
    parser = await get(session, parser_id)
    if parser is not None:
        await session.delete(parser)
        await session.commit()
        if _CACHE.get(parser_id, None):
            _CACHE.pop(parser_id)


async def get_by_spreadsheet(session: AsyncSession, spreadsheet: str) -> typing.Sequence[models.OrderSheetParse]:
    result = await session.scalars(
        sa.select(models.OrderSheetParse).where(models.OrderSheetParse.spreadsheet == spreadsheet)
    )
    return result.all()


async def get_by_spreadsheet_sheet(
    session: AsyncSession, spreadsheet: str, sheet: int
) -> models.OrderSheetParse | None:
    result = await session.scalars(
        sa.select(models.OrderSheetParse).where(
            models.OrderSheetParse.spreadsheet == spreadsheet,
            models.OrderSheetParse.sheet_id == sheet,
        )
    )
    return result.first()


async def get_by_spreadsheet_sheet_read(
    session: AsyncSession, spreadsheet: str, sheet: int
) -> models.OrderSheetParseRead | None:
    parser = await get_by_spreadsheet_sheet(session, spreadsheet, sheet)
    if parser:
        return models.OrderSheetParseRead.model_validate(parser, from_attributes=True)
    return None


async def get_default_booster(session: AsyncSession) -> models.OrderSheetParse | None:
    result = await session.scalars(
        sa.select(models.OrderSheetParse).where(models.OrderSheetParse.is_user == True)  # noqa: E712
    )
    return result.first()


async def get_default_booster_read(session: AsyncSession) -> models.OrderSheetParseRead:
    parser = await get_default_booster(session)
    if parser:
        return models.OrderSheetParseRead.model_validate(parser)
    raise RuntimeError("Default user sheet parser didn't setup")


async def get_all_not_default_user(
    session: AsyncSession,
) -> typing.Sequence[models.OrderSheetParse]:
    result = await session.scalars(
        sa.select(models.OrderSheetParse).where(models.OrderSheetParse.is_user == False)  # noqa: E712
    )
    return result.all()


async def get_all_not_default_user_read(
    session: AsyncSession,
) -> list[models.OrderSheetParseRead]:
    parsers = await get_all_not_default_user(session)
    return [models.OrderSheetParseRead.model_validate(p, from_attributes=True) for p in parsers]


async def get_all(session: AsyncSession) -> typing.Sequence[models.OrderSheetParse]:
    result = await session.scalars(sa.select(models.OrderSheetParse))
    return result.all()


async def update(
    session: AsyncSession,
    parser: models.OrderSheetParse,
    parser_in: models.OrderSheetParseUpdate,
    patch: bool = False,
) -> models.OrderSheetParse:
    update_data = parser_in.model_dump(exclude_unset=patch)
    updated_parser = await session.execute(
        sa.update(models.OrderSheetParse)
        .where(models.OrderSheetParse.id == parser.id)
        .values(**update_data)
        .returning(models.OrderSheetParse)
    )
    await session.commit()
    if _CACHE.get(parser.id, None):
        _CACHE.pop(parser.id)
    return updated_parser.scalar_one()


def get_range(parser: models.OrderSheetParseRead, *, row_id: int | None = None, end_id: int = 0) -> str:
    columns = 0
    start = 100000000000000
    for p in parser.items:
        row_p = p.row
        if row_p > columns:
            columns = row_p
        if row_p < start:
            start = row_p
    if row_id is not None:
        return f"{rowcol_to_a1(row_id, start + 1)}:{rowcol_to_a1(row_id, columns + 1)}"
    return f"{rowcol_to_a1(parser.start, start + 1)}:{rowcol_to_a1(end_id, columns + 1)}"


def generate_model(parser: models.OrderSheetParseRead):
    if _CACHE.get(parser.id, None):
        return _CACHE.get(parser.id, None)

    _fields = {}
    _validators = {}
    for getter in parser.items:
        name = getter.name
        field_type = getter.type
        _fields[getter.name] = (
            get_type(field_type, getter.null),
            None if getter.null else ...,
        )
        if getter.valid_values:
            _validators[f"{name}_parse"] = field_validator(name, mode="before")(enum_parse(name, getter.valid_values))
        elif field_type == "datetime":
            _validators[f"{name}_parse"] = field_validator(name, mode="before")(parse_datetime)
        elif field_type == "timedelta":
            _validators[f"{name}_parse"] = field_validator(name, mode="before")(parse_timedelta)

    check_model = create_model(f"CheckModel{parser.id}", **_fields, __validators__=_validators)  # type: ignore
    _CACHE[parser.id] = check_model
    return check_model


def parse_row(
    parser: models.OrderSheetParseRead,
    model: typing.Type[models.SheetEntity],
    row_id: int,
    row: list[typing.Any],
    *,
    is_raise: bool = True,
) -> models.SheetEntity | None:
    maximum = max([i.row for i in parser.items])
    for _ in range(maximum - len(row) + 1):
        row.append(None)

    data_for_valid = {}
    for getter in parser.items:
        value = row[getter.row]
        value = value if value not in ["", " "] else None
        if value is not None:
            if getter.type == "float" and isinstance(value, str):
                value = value.replace(",", ".")
            if getter.type == "str" and isinstance(value, int):
                value = str(value)
        data_for_valid[getter.name] = value
    try:
        validated_data = generate_model(parser)(**data_for_valid).model_dump()
        model_fields = []
        containers = {}
        data: dict[str, dict[str, typing.Any] | typing.Any] = {}
        for field in model.model_fields.items():
            if isinstance(field[1].annotation, ModelMetaclass):
                data[field[0]] = {}
                containers[field[0]] = [field[0] for field in field[1].annotation.model_fields.items()]  # noqa
            else:
                model_fields.append(field[0])
        for getter in parser.items:
            if getter.name in model_fields:
                data[getter.name] = validated_data[getter.name]
            else:
                for key, fields in containers.items():
                    if getter.name in fields:
                        data[key][getter.name] = validated_data[getter.name]
                        break
        return model(
            spreadsheet=parser.spreadsheet,
            sheet_id=parser.sheet_id,
            row_id=row_id,
            **data,
        )
    except ValidationError as error:
        if is_raise:
            logger.error(f"Spreadsheet={parser.spreadsheet} sheet_id={parser.sheet_id} row_id={row_id}")
            logger.error(errors.APIValidationError.from_pydantic(error).model_dump_json(indent=4))
            raise error
        else:
            return None


def data_to_row(parser: models.OrderSheetParseRead, to_dict: dict) -> dict[int, typing.Any]:
    row = {}
    data = {}

    def set_value(set_key, to_set):
        if isinstance(to_set, datetime.datetime):
            data[set_key] = to_set.strftime(config.app.datetime_format_sheets)
        else:
            data[set_key] = to_set

    for key, value in to_dict.items():
        if isinstance(value, dict):
            for key_2, value_2 in value.items():
                set_value(key_2, value_2)
        else:
            set_value(key, value)

    for getter in parser.items:
        if not getter.generated and getter.name in to_dict.keys():
            to_insert = data[getter.name] if data[getter.name] is not None else ""
            row[getter.row] = jsonable_encoder(to_insert)
    return row


def parse_all_data(
    model: typing.Type[models.SheetEntity],
    spreadsheet: str,
    sheet_id: int,
    rows_in: list[list[typing.Any]],
    parser_in: models.OrderSheetParseRead,
    is_raise: bool = False,
) -> list[BaseModel]:
    t = time.time()
    resp: list[BaseModel] = []
    for row_id, row in enumerate(rows_in, parser_in.start):
        data = parse_row(parser_in, model, row_id, row, is_raise=is_raise)
        if data:
            resp.append(data)
    logger.info(f"Parsing data from spreadsheet={spreadsheet} sheet_id={sheet_id} completed in {time.time() - t}")
    return resp


def get_all_data(
    creds: models.AdminGoogleTokenDB,
    model: typing.Type[models.SheetEntity],
    parser: models.OrderSheetParseRead,
    is_raise: bool = False,
) -> list[BaseModel]:
    gc = gspread.service_account_from_dict(creds)
    sh = gc.open(parser.spreadsheet)
    sheet = sh.get_worksheet_by_id(parser.sheet_id)
    values_list = sheet.col_values(2, value_render_option=ValueRenderOption.unformatted)
    index = 0
    for i in range(parser.start, len(values_list)):
        if not values_list[i]:
            break
        index = i
    rows = sheet.get(
        get_range(parser, end_id=index + 1),
        value_render_option=ValueRenderOption.unformatted,
        date_time_render_option=DateTimeOption.formatted_string,
    )
    return parse_all_data(model, parser.spreadsheet, parser.sheet_id, rows, parser, is_raise=is_raise)


def update_rows_data(
    creds: models.AdminGoogleTokenDB,
    parser: models.OrderSheetParseRead,
    data: list[tuple[int, dict]],
) -> None:
    gc = gspread.service_account_from_dict(creds)
    sh = gc.open(parser.spreadsheet)
    sheet = sh.get_worksheet_by_id(parser.sheet_id)
    data_range = []

    for row_id, d in data:
        row = data_to_row(parser, d)
        for col, value in row.items():
            data_range.append({"range": rowcol_to_a1(row_id, col + 1), "values": [[value]]})

    sheet.batch_update(
        data_range,
        value_input_option=ValueInputOption.user_entered,
        response_value_render_option=ValueRenderOption.formatted,
        response_date_time_render_option=DateTimeOption.formatted_string,
    )


def clear_rows_data(creds: models.AdminGoogleTokenDB, parser: models.OrderSheetParseRead, row_id: int) -> None:
    gc = gspread.service_account_from_dict(creds)
    sh = gc.open(parser.spreadsheet)
    sheet = sh.get_worksheet_by_id(parser.sheet_id)
    data_range = []
    for item in parser.items:
        if not item.generated:
            data_range.append({"range": rowcol_to_a1(row_id, item.row + 1), "values": [[""]]})
    sheet.batch_update(
        data_range,
        response_value_render_option=ValueRenderOption.formatted,
        response_date_time_render_option=DateTimeOption.formatted_string,
    )


def get_row_data(
    model: typing.Type[models.SheetEntity],
    creds: models.AdminGoogleTokenDB,
    parser: models.OrderSheetParseRead,
    row_id: int,
    *,
    is_raise=True,
) -> models.SheetEntity:
    gc = gspread.service_account_from_dict(creds)
    sh = gc.open(parser.spreadsheet)
    sheet = sh.get_worksheet_by_id(parser.sheet_id)
    row = sheet.get(
        get_range(parser, row_id=row_id),
        value_render_option=ValueRenderOption.unformatted,
        date_time_render_option=DateTimeOption.formatted_string,
    )
    return parse_row(parser, model, row_id, row[0], is_raise=is_raise)  # type: ignore


def update_row_data(
    creds: models.AdminGoogleTokenDB,
    parser: models.OrderSheetParseRead,
    row_id: int,
    data: dict,
) -> None:
    gc = gspread.service_account_from_dict(creds)
    sh = gc.open(parser.spreadsheet)
    sheet = sh.get_worksheet_by_id(parser.sheet_id)
    row = data_to_row(parser, data)
    sheet.batch_update(
        [{"range": rowcol_to_a1(row_id, col + 1), "values": [[value]]} for col, value in row.items()],
        value_input_option=ValueInputOption.user_entered,
        response_value_render_option=ValueRenderOption.formatted,
        response_date_time_render_option=DateTimeOption.formatted_string,
    )


def create_row_data(
    model: typing.Type[models.SheetEntity],
    creds: models.AdminGoogleTokenDB,
    parser: models.OrderSheetParseRead,
    data: dict,
) -> BaseModel:
    gc = gspread.service_account_from_dict(creds)
    sh = gc.open(parser.spreadsheet)
    sheet = sh.get_worksheet_by_id(parser.sheet_id)
    values_list = sheet.col_values(2, value_render_option=ValueRenderOption.unformatted)
    index = 1

    for value in values_list:
        if not value:
            break
        index += 1

    if index < parser.start:
        index = parser.start

    update_row_data(creds, parser, index, data)
    return get_row_data(model, creds, parser, index)


def find_by(
    model: typing.Type[models.SheetEntity],
    creds: models.AdminGoogleTokenDB,
    parser: models.OrderSheetParseRead,
    value,
) -> models.SheetEntity | None:
    gc = gspread.service_account_from_dict(creds)
    sh = gc.open(parser.spreadsheet)
    sheet = sh.get_worksheet_by_id(parser.sheet_id)
    row = sheet.find(str(value))
    if row:
        return get_row_data(model, creds, parser, row.row)
    return None


def create_or_update_booster(
    creds: models.AdminGoogleTokenDB,
    parser: models.OrderSheetParseRead,
    value: str,
    user: dict,
):
    parser = models.OrderSheetParseRead.model_validate(parser)
    booster = find_by(models.UserReadSheets, creds, parser, value)
    if booster:
        update_row_data(creds, parser, booster.row_id, user)
    else:
        create_row_data(models.UserReadSheets, creds, parser, user)


def delete_booster(
    creds: models.AdminGoogleTokenDB,
    parser: models.OrderSheetParseRead,
    value: str,
) -> None:
    parser = models.OrderSheetParseRead.model_validate(parser)
    booster = find_by(models.UserReadSheets, creds, parser, value)
    if booster:
        clear_row(creds, parser, booster.row_id)


def clear_row(creds: models.AdminGoogleTokenDB, parser: models.OrderSheetParseRead, row_id: int) -> None:
    parser = models.OrderSheetParseRead.model_validate(parser)
    clear_rows_data(creds, parser, row_id)


def get_cell(creds: models.AdminGoogleTokenDB, spreadsheet: str, sheet_id: int, cell: str) -> str:
    gc = gspread.service_account_from_dict(creds)
    sh = gc.open(spreadsheet)
    sheet = sh.get_worksheet_by_id(sheet_id)
    value = sheet.acell(cell)
    return value.value


async def create_token(
    session: AsyncSession, user: models.User, token: models.AdminGoogleToken
) -> models.GoogleTokenUser:
    token = models.GoogleTokenUser(user_id=user.id, token=token.model_dump(mode="json"))
    session.add(token)
    await session.commit()
    return token


async def get_token(session: AsyncSession, user: models.User) -> models.GoogleTokenUser | None:
    result = await session.scalars(sa.select(models.GoogleTokenUser).where(models.GoogleTokenUser.user_id == user.id))
    return result.first()


async def get_first_superuser_token(session: AsyncSession) -> models.GoogleTokenUser:
    result = await session.scalars(
        sa.select(models.GoogleTokenUser).where(models.GoogleTokenUser.user.has(name=config.app.super_user_username))
    )
    return result.one()


def get_first_superuser_token_sync(session: Session) -> models.GoogleTokenUser:
    result = session.scalars(
        sa.select(models.GoogleTokenUser).where(models.GoogleTokenUser.user.has(name=config.app.super_user_username))
    )
    return result.one()
