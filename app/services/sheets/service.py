import time
import typing
import datetime

from loguru import logger
from pydantic import SecretStr, EmailStr, HttpUrl, ValidationError, field_validator, BaseModel, create_model
from pydantic._internal._model_construction import ModelMetaclass
from pydantic_extra_types.payment import PaymentCardNumber
from pydantic_extra_types.phone_numbers import PhoneNumber
from beanie import PydanticObjectId

from app.core import errors
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
    if _CACHE.get(parser.id, None):
        _CACHE.pop(parser.id)
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


def generate_model(parser: models.OrderSheetParse):
    if _CACHE.get(parser.id, None):
        return _CACHE.get(parser.id, None)

    _fields = {}
    _validators = {}
    for getter in parser.items:
        name = getter.name
        field_type = getter.type
        _fields[getter.name] = (get_type(field_type, getter.null), None if getter.null else ...)
        if getter.valid_values:
            _validators[f"{name}_parse"] = (field_validator(name, mode="before")
                                            (enum_parse(name, getter.valid_values)))
        elif field_type == "datetime":
            _validators[f"{name}_parse"] = (field_validator(name, mode="before")(parse_datetime))
        elif field_type == "timedelta":
            _validators[f"{name}_parse"] = (field_validator(name, mode="before")(parse_timedelta))

    check_model = create_model(f"CheckModel{parser.id}", **_fields, __validators__=_validators)  # type: ignore
    _CACHE[parser.id] = check_model
    return check_model


def parse_row(
        parser: models.OrderSheetParse,
        model: typing.Type[models.SheetEntity],
        spreadsheet: str,
        sheet_id: int,
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
        data_for_valid[getter.name] = value if value not in ["", " "] else None
    try:
        valid_model = generate_model(parser)(**data_for_valid)
    except ValidationError as error:
        if is_raise:
            logger.error(f"Spreadsheet={spreadsheet} sheet_id={sheet_id} row_id={row_id}")
            logger.error(errors.APIValidationError.from_pydantic(error))
            raise error
            # return
        else:
            return
    validated_data = valid_model.model_dump()
    model_fields = []
    containers = {}
    data = {"extra": {}, "spreadsheet": spreadsheet, "sheet_id": sheet_id, "row_id": row_id}

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
            # else:
            #     data["extra"][getter.name] = validated_data[getter.name]
    try:
        return model.model_validate(data)
    except ValidationError as error:
        if is_raise:
            logger.error(f"Spreadsheet={spreadsheet} sheet_id={sheet_id} row_id={row_id}")
            logger.error(errors.APIValidationError.from_pydantic(error))
            raise error
            # return
        else:
            return


def parse_all_data(model: BM, spreadsheet: str, sheet_id: int, rows_in, parser_in: models.OrderSheetParse):
    t = time.time()
    resp = []
    for row_id, row in enumerate(rows_in, parser_in.start):
        data = parse_row(parser_in, model, spreadsheet, sheet_id, row_id, row, is_raise=False)
        if data:
            resp.append(data)
    logger.info(f"Parsing data from spreadsheet={spreadsheet} sheet_id={sheet_id} completed in {time.time() - t}")
    return resp
