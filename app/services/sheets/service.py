import datetime
import time
import typing

import gspread
from beanie import PydanticObjectId
from gspread.utils import DateTimeOption, ValueInputOption, ValueRenderOption
from loguru import logger
from pydantic import (BaseModel, EmailStr, HttpUrl, SecretStr, ValidationError,
                      create_model, field_validator)
from pydantic._internal._model_construction import ModelMetaclass
from pydantic_extra_types.payment import PaymentCardNumber
from pydantic_extra_types.phone_numbers import PhoneNumber

from app.core import errors
from app.services.auth import models as auth_models
from app.services.time import service as time_servie

from . import models

type_map = {
    "int": int,
    'str': str,
    'float': float,
    'bool': bool,
    'timedelta': datetime.timedelta,
    'datetime': datetime.datetime,
    'SecretStr': SecretStr,
    'EmailStr': EmailStr,
    'HttpUrl': HttpUrl,
    'PhoneNumber': PhoneNumber,
    'PaymentCardNumber': PaymentCardNumber
}

BM = typing.TypeVar("BM", bound=BaseModel)

_CACHE: dict = {}


def enum_parse(field, extra):
    def decorator(v: str, ):
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
    now = datetime.datetime.utcnow()
    converted_time = time_servie.convert_time(v, now=now, conversion_mode=time_servie.ConversionMode.RELATIVE)
    return converted_time - now


def get_type(type_name: str, null: bool):
    if '|' in type_name:
        names = type_name.split('|')
        return get_type(names[0].strip(), False) | get_type(names[1].strip(), null)

    if null:
        return type_map[type_name] | None
    return type_map[type_name]


async def get(parser_id: PydanticObjectId) -> models.OrderSheetParse | None:
    return await models.OrderSheetParse.find_one({"_id": parser_id})


async def create(parser_in: models.OrderSheetParseCreate):
    parser = models.OrderSheetParse(**parser_in.model_dump())
    return await parser.create()


async def delete(parser_id: PydanticObjectId):
    user_order = await models.OrderSheetParse.get(parser_id)
    await user_order.delete()
    if _CACHE.get(parser_id, None):
        _CACHE.pop(parser_id)


async def get_by_spreadsheet(spreadsheet: str):
    return await models.OrderSheetParse.find({"spreadsheet": spreadsheet}).to_list()


async def get_by_spreadsheet_sheet(spreadsheet: str, sheet: int) -> models.OrderSheetParse | None:
    return await models.OrderSheetParse.find_one({"spreadsheet": spreadsheet, "sheet_id": sheet})


async def get_default_booster() -> models.OrderSheetParse | None:
    return await models.OrderSheetParse.find_one({"is_user": True})


async def get_all_not_default_booster() -> list[models.OrderSheetParse]:
    return await models.OrderSheetParse.find({"is_user": False}).to_list()


async def get_all() -> list[models.OrderSheetParse]:
    return await models.OrderSheetParse.find({}).to_list()


async def update(parser: models.OrderSheetParse, parser_in: models.OrderSheetParseUpdate):
    parser_data = parser.model_dump()
    update_data = parser_in.model_dump(exclude_none=True)

    for field in parser_data:
        if field in update_data:
            setattr(parser, field, update_data[field])

    await parser.save_changes()
    if _CACHE.get(parser.id, None):
        _CACHE.pop(parser.id)
    return parser


def n2a(n: int):
    d, m = divmod(n, 26)  # 26 is the number of ASCII letters
    return '' if n < 0 else n2a(d - 1) + chr(m + 65)  # chr(65) = 'A'


def get_range(parser: models.OrderSheetParseRead, *, row_id: int = None, end_id: int = 0):
    columns = 0
    start = 100000000000000
    for p in parser.items:
        row_p = p.row
        if row_p > columns:
            columns = row_p
        if row_p < start:
            start = row_p
    if row_id:
        return f"{n2a(start)}{row_id}:{n2a(columns)}{row_id}"
    return f"{n2a(start)}{parser.start}:{n2a(columns)}{end_id}"


def generate_model(parser: models.OrderSheetParseRead):
    if _CACHE.get(parser.id, None):
        return _CACHE.get(parser.id, None)

    _fields = {}
    _validators = {}
    for getter in parser.items:
        name = getter.name
        field_type = getter.type
        _fields[getter.name] = (get_type(field_type, getter.null), None if getter.null else ...)
        if getter.valid_values:
            _validators[f"{name}_parse"] = (field_validator(name, mode="before")(enum_parse(name, getter.valid_values)))
        elif field_type == "datetime":
            _validators[f"{name}_parse"] = (field_validator(name, mode="before")(parse_datetime))
        elif field_type == "timedelta":
            _validators[f"{name}_parse"] = (field_validator(name, mode="before")(parse_timedelta))

    check_model = create_model(f"CheckModel{parser.id}", **_fields, __validators__=_validators)  # type: ignore
    _CACHE[parser.id] = check_model
    return check_model


def parse_row(
        parser: models.OrderSheetParse | models.OrderSheetParseRead,
        model: typing.Type[models.SheetEntity],
        row_id: int,
        row: list[typing.Any],
        *,
        is_raise: bool = True
) -> BM | None:
    for i in range(len(parser.items) - len(row)):
        row.append(None)

    data_for_valid = {}
    for getter in parser.items:
        value = row[getter.row]
        # if getter.type == "float" and isinstance(value, str):
        #     value = value.replace(',', '.')
        data_for_valid[getter.name] = value if value not in ["", " "] else None
    try:
        valid_model = generate_model(parser)(**data_for_valid)
    except ValidationError as error:
        if is_raise:
            logger.error(f"Spreadsheet={parser.spreadsheet} sheet_id={parser.sheet_id} row_id={row_id}")
            logger.error(errors.APIValidationError.from_pydantic(error))
            raise error
        else:
            return
    validated_data = valid_model.model_dump()
    model_fields = []
    containers = {}
    data = {"spreadsheet": parser.spreadsheet, "sheet_id": parser.sheet_id, "row_id": row_id}

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
    try:
        return model.model_validate(data)
    except ValidationError as error:
        if is_raise:
            logger.error(f"Spreadsheet={parser.spreadsheet} sheet_id={parser.sheet_id} row_id={row_id}")
            logger.error(errors.APIValidationError.from_pydantic(error))
            raise error
            # return
        else:
            return


def data_to_row(parser: models.OrderSheetParseRead, to_dict: dict) -> dict[int, typing.Any]:
    row = {}
    data = {}

    if to_dict.get("_id"):
        to_dict["id"] = to_dict.pop("_id")

    for key, value in to_dict.items():
        if isinstance(value, dict):
            for key_2, value_2 in value.items():
                data[key_2] = value_2
        else:
            data[key] = value

    for getter in parser.items:
        if not getter.generated and data.get(getter.name) is not None:
            row[getter.row] = data[getter.name]
    return row


def parse_all_data(
        model: typing.Type[models.SheetEntity],
        spreadsheet: str,
        sheet_id: int,
        rows_in: list[list],
        parser_in: models.OrderSheetParseRead
):
    t = time.time()
    resp: list[BM] = []
    for row_id, row in enumerate(rows_in, parser_in.start):
        data = parse_row(parser_in, model, row_id, row, is_raise=True)
        if data:
            resp.append(data)
    logger.info(f"Parsing data from spreadsheet={spreadsheet} sheet_id={sheet_id} completed in {time.time() - t}")
    return resp


def get_all_data(
        creds: auth_models.AdminGoogleToken,
        model: typing.Type[models.SheetEntity],
        parser: models.OrderSheetParseRead
):
    gc = gspread.service_account_from_dict(creds.model_dump())
    sh = gc.open(parser.spreadsheet)
    sheet = sh.get_worksheet_by_id(parser.sheet_id)
    values_list = sheet.col_values(2, value_render_option=ValueRenderOption.unformatted)
    index = 0
    for i in range(parser.start, len(values_list)):
        if not values_list[i]:
            break
        index = i
    rows = sheet.get(get_range(parser, end_id=index + 1),
                     value_render_option=ValueRenderOption.unformatted,
                     date_time_render_option=DateTimeOption.formatted_string)
    return parse_all_data(model, parser.spreadsheet, parser.sheet_id, rows, parser)


def update_rows_data(
        creds: auth_models.AdminGoogleToken,
        parser: models.OrderSheetParseRead,
        data: list[tuple[int, dict]]
):
    gc = gspread.service_account_from_dict(creds.model_dump())
    sh = gc.open(parser.spreadsheet)
    sheet = sh.get_worksheet_by_id(parser.sheet_id)
    data_range = []

    for row_id, d in data:
        row = data_to_row(parser, d)
        for col, value in row.items():
            data_range.append({"range": f"{n2a(col)}{row_id}", "values": [[value]]})

    sheet.batch_update(
        data_range,
        response_value_render_option=ValueRenderOption.formatted,
        response_date_time_render_option=DateTimeOption.formatted_string
    )


def clear_rows_data(
        creds: auth_models.AdminGoogleToken,
        parser: models.OrderSheetParseRead,
        row_id: int
):
    gc = gspread.service_account_from_dict(creds.model_dump())
    sh = gc.open(parser.spreadsheet)
    sheet = sh.get_worksheet_by_id(parser.sheet_id)
    data_range = []
    for item in parser.items:
        if not item.generated:
            data_range.append({"range": f"{n2a(item.row)}{row_id}", "values": [['']]})
    sheet.batch_update(
        data_range,
        response_value_render_option=ValueRenderOption.formatted,
        response_date_time_render_option=DateTimeOption.formatted_string
    )


def get_row_data(
        model: typing.Type[models.SheetEntity],
        creds: auth_models.AdminGoogleToken,
        parser: models.OrderSheetParseRead,
        row_id: int,
        *,
        is_raise=True
) -> BM:
    gc = gspread.service_account_from_dict(creds.model_dump())
    sh = gc.open(parser.spreadsheet)
    sheet = sh.get_worksheet_by_id(parser.sheet_id)
    row = sheet.get(get_range(parser, row_id=row_id),
                    value_render_option=ValueRenderOption.unformatted,
                    date_time_render_option=DateTimeOption.formatted_string)
    return parse_row(parser, model, row_id, row[0], is_raise=is_raise)


def update_row_data(
        creds: auth_models.AdminGoogleToken,
        parser: models.OrderSheetParseRead,
        row_id: int,
        data: dict
):
    gc = gspread.service_account_from_dict(creds.model_dump())
    sh = gc.open(parser.spreadsheet)
    sheet = sh.get_worksheet_by_id(parser.sheet_id)
    row = data_to_row(parser, data)
    sheet.batch_update(
        [{"range": f"{n2a(col)}{row_id}", "values": [[value]]} for col, value in row.items()],
        value_input_option=ValueInputOption.user_entered,
        response_value_render_option=ValueRenderOption.formatted,
        response_date_time_render_option=DateTimeOption.formatted_string
    )


def create_row_data(
        model: typing.Type[models.SheetEntity],
        creds: auth_models.AdminGoogleToken,
        parser: models.OrderSheetParseRead,
        data: dict
):
    gc = gspread.service_account_from_dict(creds.model_dump())
    sh = gc.open(parser.spreadsheet)
    sheet = sh.get_worksheet_by_id(parser.sheet_id)
    values_list = sheet.col_values(2, value_render_option=ValueRenderOption.unformatted)
    index = 1

    for value in values_list:
        if not value:
            break
        index += 1

    update_row_data(creds, parser, index, data)
    return get_row_data(model, creds, parser, index)


def find_by(
        model: typing.Type[models.SheetEntity],
        creds: auth_models.AdminGoogleToken,
        parser: models.OrderSheetParseRead,
        value
) -> models.SheetEntity:
    gc = gspread.service_account_from_dict(creds.model_dump())
    sh = gc.open(parser.spreadsheet)
    sheet = sh.get_worksheet_by_id(parser.sheet_id)
    row = sheet.find(str(value))
    if row:
        return get_row_data(model, creds, parser, row.row)


def create_or_update_booster(
        creds: auth_models.AdminGoogleToken,
        parser: models.OrderSheetParseRead,
        value: str,
        user: dict,
):
    parser = models.OrderSheetParseRead.model_validate(parser)
    creds = auth_models.AdminGoogleToken.model_validate(creds)
    booster = find_by(auth_models.UserReadSheets, creds, parser, value)
    if booster:
        update_row_data(creds, parser, booster.row_id, user)
    else:
        create_row_data(auth_models.UserReadSheets, creds, parser, user)


def delete_booster(
        creds: auth_models.AdminGoogleToken,
        parser: models.OrderSheetParseRead,
        value: str,
):
    parser = models.OrderSheetParseRead.model_validate(parser)
    creds = auth_models.AdminGoogleToken.model_validate(creds)
    booster = find_by(auth_models.UserReadSheets, creds, parser, value)
    if booster:
        clear_row(creds, parser, booster.row_id)


def clear_row(
        creds: auth_models.AdminGoogleToken,
        parser: models.OrderSheetParseRead,
        row_id: int
):
    parser = models.OrderSheetParseRead.model_validate(parser)
    creds = auth_models.AdminGoogleToken.model_validate(creds)
    clear_rows_data(creds, parser, row_id)
