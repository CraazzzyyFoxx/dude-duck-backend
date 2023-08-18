import typing
import datetime

from pydantic import SecretStr, EmailStr, HttpUrl
from pydantic_extra_types.payment import PaymentCardNumber
from pydantic_extra_types.phone_numbers import PhoneNumber
from beanie import PydanticObjectId

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


async def get(order_id: PydanticObjectId) -> models.OrderSheetParse:
    return await models.OrderSheetParse.find_one({"_id": order_id})


async def create(parser_in: models.OrderSheetParseCreate):
    parser = models.OrderSheetParse(**parser_in.model_dump())
    return await parser.create()


async def delete(parser_id: PydanticObjectId):
    user_order = await models.OrderSheetParse.get(parser_id)
    await user_order.delete()


async def get_by_spreadsheet(spreadsheet: str):
    return await models.OrderSheetParse.find({"spreadsheet": spreadsheet}).to_list()


async def get_by_spreadsheet_sheet(spreadsheet: str, sheet: int):
    return await models.OrderSheetParse.find_one({"spreadsheet": spreadsheet, "sheet_id": sheet})


async def get_default_booster() -> models.OrderSheetParse:
    return await models.OrderSheetParse.find_one({"default": "booster"})


async def get_all_not_default_booster() -> list[models.OrderSheetParse]:
    return await models.OrderSheetParse.find({"default": {"$ne": "booster"}}).to_list()


async def get_all() -> list[models.OrderSheetParse]:
    return await models.OrderSheetParse.find({}).to_list()


async def update(parser: models.OrderSheetParse, parser_in: models.OrderSheetParseUpdate):
    parser_data = parser.model_dump()
    update_data = parser_in.model_dump(exclude_none=True)

    for field in parser_data:
        if field in update_data:
            setattr(parser, field, update_data[field])

    await parser.save_changes()
    return parser


def n2a(n: int):
    d, m = divmod(n, 26)  # 26 is the number of ASCII letters
    return '' if n < 0 else n2a(d - 1) + chr(m + 65)  # chr(65) = 'A'


def get_range(parser: models.OrderSheetParse, *, row_id: int = None, end_id: int = 0):
    columns = 0
    start = 100000000000
    for p in parser.items:
        row_p = p.row
        if row_p > columns:
            columns = row_p
        if row_p < start:
            start = row_p
    if row_id:
        return f"{n2a(start)}{row_id}:{n2a(columns)}{row_id}"
    return f"{n2a(start)}{parser.start}:{n2a(columns)}{end_id}"
