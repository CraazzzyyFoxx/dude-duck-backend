import typing

from fastapi import HTTPException
from loguru import logger
from fastapi.encoders import jsonable_encoder
from gspread_asyncio import AsyncioGspreadClientManager
from google.oauth2.service_account import Credentials  # noqa
from gspread.utils import ValueRenderOption, DateTimeOption, ValueInputOption
from pydantic import create_model, field_validator, BaseModel, ValidationError
from pydantic._internal._model_construction import ModelMetaclass  # noqa
from beanie import PydanticObjectId
from starlette import status

from app.core import config, errors
from app.services.auth import models as auth_models
from app.services.orders import models as orders_models


from . import models, service

__all__ = ("GoogleSheetsService", "GoogleSheetsServiceManager")

BM = typing.TypeVar("BM", bound=BaseModel)


class GoogleSheetsServiceManagerMeta:
    def __init__(self):
        self.managers: dict[str, GoogleSheetsService] = {}
        self.cache: dict[PydanticObjectId, typing.Type[BaseModel]] = {}
        with open(config.GOOGLE_CONFIG_FILE) as file:
            self.creds = auth_models.AdminGoogleToken.model_validate_json(file.read()).model_dump()

    def generate_model(self, parser: models.OrderSheetParse):
        if model := self.cache.get(parser.id):
            return model

        _fields = {}
        _validators = {}
        for getter in parser.items:
            name = getter.name
            field_type = getter.type
            _fields[getter.name] = (service.get_type(field_type, getter.null), None if getter.null else ...)
            if getter.valid_values:
                _validators[f"{name}_parse"] = (field_validator(name, mode="before")
                                                (service.enum_parse(name, getter.valid_values)))
            elif field_type == "datetime":
                _validators[f"{name}_parse"] = (field_validator(name, mode="before")(service.parse_datetime))
            elif field_type == "timedelta":
                _validators[f"{name}_parse"] = (field_validator(name, mode="before")(service.parse_timedelta))

        check_model = create_model(f"CheckModel{parser.id}", **_fields, __validators__=_validators)  # type: ignore
        self.cache[parser.id] = check_model
        return check_model

    def delete_from_cache(self, parser: models.OrderSheetParse):
        if self.cache.get(parser.id):
            self.cache.pop(parser.id)

    async def init(self):
        self.managers["0"] = GoogleSheetsService(AsyncioGspreadClientManager(self.get_creds()))

        admins = await auth_models.User.find({"is_superuser": True, "google": {"$ne": None}}).to_list()
        for admin in admins:
            self.managers[admin.google.client_id] = GoogleSheetsService(
                AsyncioGspreadClientManager(self.get_creds(admin=admin))
            )
        logger.info("GoogleSheetsServiceManager... Ready!")

    async def admin_create(self, user: auth_models.User):
        self.managers[user.google.client_id] = GoogleSheetsService(
            AsyncioGspreadClientManager(self.get_creds(admin=user)))

    async def admin_delete(self, user: auth_models.User):
        del self.managers[user.google.client_id]

    def get_creds(self, *, admin=None):
        if admin is not None:
            data = admin.google.model_dump()
        else:
            data = self.creds

        def wrapped():
            creds = Credentials.from_service_account_info(data)
            scoped = creds.with_scopes([
                "https://spreadsheets.google.com/feeds",
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive",
            ])
            return scoped

        return wrapped

    def get(self, *, user: auth_models.User = None) -> 'GoogleSheetsService':
        return self.managers[user.google.client_id] if user else self.managers["0"]


class GoogleSheetsService:
    def __init__(self, manager: AsyncioGspreadClientManager):
        self.manager = manager

    @staticmethod
    async def get_parser(spreadsheet: str, sheet_id: int):
        if parser := await service.get_by_spreadsheet_sheet(spreadsheet, sheet_id):
            return parser
        raise ValueError(f"No data for parser [spreadsheet={spreadsheet} sheet_id={sheet_id}]")

    async def parse_row(
            self,
            model: typing.Type[models.SheetEntity],
            spreadsheet: str,
            sheet_id: int,
            row_id: int,
            row: list[typing.Any],
            *,
            is_raise: bool = True
    ) -> BM | None:
        parser = await self.get_parser(spreadsheet, sheet_id)
        for i in range(len(parser.items) - len(row)):
            row.append(None)

        data_for_valid = {}
        for getter in parser.items:
            value = row[getter.row]
            data_for_valid[getter.name] = value if value not in ["", " "] else None
        try:
            valid_model = GoogleSheetsServiceManager.generate_model(parser).model_validate(data_for_valid)
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
                else:
                    data["extra"][getter.name] = validated_data[getter.name]
        try:
            return model(**data)
        except ValidationError as error:
            if is_raise:
                logger.error(f"Spreadsheet={spreadsheet} sheet_id={sheet_id} row_id={row_id}")
                logger.error(errors.APIValidationError.from_pydantic(error))
                raise error
                # return
            else:
                return

    async def data_to_row(
            self,
            spreadsheet: str,
            sheet_id: int,
            data: BaseModel
    ) -> dict[int, typing.Any]:
        parser = await self.get_parser(spreadsheet, sheet_id)
        to_dict: dict = jsonable_encoder(data)

        if to_dict.get("_id"):
            to_dict["id"] = to_dict.pop("_id")

        row = {}
        data = {}

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

    async def get_row_data(
            self,
            model: typing.Type[models.SheetEntity],
            spreadsheet: str,
            sheet_id: int,
            row_id: int,
            *,
            is_raise=True
    ) -> BM:
        agc = await self.manager.authorize()
        sh = await agc.open(spreadsheet)
        sheet = await sh.get_worksheet_by_id(sheet_id)
        parser = await self.get_parser(spreadsheet, sheet_id)
        row = await sheet.get(range_name=service.get_range(parser, row_id=row_id),
                              value_render_option=ValueRenderOption.unformatted,
                              date_time_render_option=DateTimeOption.formatted_string)
        return await self.parse_row(model, spreadsheet, sheet_id, row_id, row[0], is_raise=is_raise)

    async def get_all_data(
            self,
            model: typing.Type[models.SheetEntity],
            spreadsheet: str,
            sheet_id: int,
    ):
        agc = await self.manager.authorize()
        sh = await agc.open(spreadsheet)
        sheet = await sh.get_worksheet_by_id(sheet_id)
        parser = await self.get_parser(spreadsheet, sheet_id)
        values_list = await sheet.col_values(2, value_render_option=ValueRenderOption.unformatted)
        index = 0
        for i in range(parser.start, len(values_list)):
            if not values_list[i]:
                break
            index = i
        rows = await sheet.get(range_name=service.get_range(parser, end_id=index),
                               value_render_option=ValueRenderOption.unformatted,
                               date_time_render_option=DateTimeOption.formatted_string)
        resp = []
        for row_id, row in enumerate(rows, parser.start):
            data = await self.parse_row(model, spreadsheet, sheet_id, row_id, row, is_raise=False)
            if data:
                resp.append(data)

        return resp

    async def create_row_data(
            self,
            model: typing.Type[models.SheetEntity],
            spreadsheet: str,
            sheet_id: int,
            data: BaseModel,
    ) -> BM:
        agc = await self.manager.authorize()
        sh = await agc.open(spreadsheet)
        sheet = await sh.get_worksheet_by_id(sheet_id)
        values_list = await sheet.col_values(2, value_render_option=ValueRenderOption.unformatted)
        index = 1

        for value in values_list:
            if not value:
                break
            index += 1

        return await self.update_row_data(model, spreadsheet, sheet_id, index, data)

    async def update_row_data(
            self,
            model: typing.Type[models.SheetEntity],
            spreadsheet: str,
            sheet_id: int,
            row_id: int,
            data: BaseModel,
    ) -> BM:
        agc = await self.manager.authorize()
        sh = await agc.open(spreadsheet)
        sheet = await sh.get_worksheet_by_id(sheet_id)
        row = await self.data_to_row(spreadsheet, sheet_id, data)
        await sheet.batch_update(
            [{"range": f"{service.n2a(col)}{row_id}", "values": [[value]]} for col, value in row.items()],
            value_input_option=ValueInputOption.user_entered,
            response_value_render_option=ValueRenderOption.formatted,
            response_date_time_render_option=DateTimeOption.formatted_string
        )

        return await self.get_row_data(model, spreadsheet, sheet_id, row_id)

    async def update_rows_data(
            self,
            spreadsheet: str,
            sheet_id: int,
            data: list[tuple[int, BaseModel]],
    ):
        agc = await self.manager.authorize()
        sh = await agc.open(spreadsheet)
        sheet = await sh.get_worksheet_by_id(sheet_id)
        data_range = []

        for row_id, d in data:
            row = await self.data_to_row(spreadsheet, sheet_id, d)
            for col, value in row.items():
                data_range.append({"range": f"{service.n2a(col)}{row_id}", "values": [[value]]})

        await sheet.batch_update(
            data_range,
            response_value_render_option=ValueRenderOption.formatted,
            response_date_time_render_option=DateTimeOption.formatted_string
        )

    async def find_by(
            self,
            model: typing.Type[models.SheetEntity],
            spreadsheet: str,
            sheet_id: int,
            value):
        agc = await self.manager.authorize()
        sh = await agc.open(spreadsheet)
        sheet = await sh.get_worksheet_by_id(sheet_id)
        row = await sheet.find(str(value))
        if row:
            return await self.get_row_data(model, spreadsheet, sheet_id, row.row)


GoogleSheetsServiceManager = GoogleSheetsServiceManagerMeta()


async def get_order_from_sheets(data: models.SheetEntity, user: auth_models.User):
    if not user.google:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail=[{"msg": "Google Service account doesn't setup."}])
    try:
        model = await GoogleSheetsServiceManager.get(user=user).get_row_data(
            orders_models.Order, data.spreadsheet, data.sheet_id, data.row_id)
    except ValidationError as error:
        raise errors.GoogleSheetsParserError.http_exception(orders_models.Order,
                                                            data.spreadsheet, data.sheet_id, data.row_id, error)
    return model
