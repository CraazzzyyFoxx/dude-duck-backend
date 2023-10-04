from datetime import datetime

import orjson
from pydantic import BaseModel, ConfigDict, Field, constr
from tortoise import fields

from app.core.db import TimeStampMixin


class ApiLayerCurrencyToken(BaseModel):
    token: str
    uses: int = 0
    last_use: datetime = Field(default_factory=datetime.utcnow)


class AvailableCurrency(BaseModel):
    name: constr(to_upper=True)
    precision: int


default_currencies = [
    AvailableCurrency(name="USD", precision=2),
    AvailableCurrency(name="RUB", precision=0),
    AvailableCurrency(name="WOW", precision=0),
]


def decode_api_layer_currency(data: str):
    return [ApiLayerCurrencyToken.model_validate(d) for d in orjson.loads(data)]


def decode_currencies(data: str):
    return [AvailableCurrency.model_validate(d) for d in orjson.loads(data)]


def encode_api_layer_currency(data: list[ApiLayerCurrencyToken]):
    return orjson.dumps([d.model_dump() for d in data]).decode()


def encode_currencies(data: list[AvailableCurrency]):
    return orjson.dumps([d.model_dump() for d in data]).decode()


class Settings(TimeStampMixin):
    api_layer_currency: list[ApiLayerCurrencyToken] = fields.JSONField(
        decoder=decode_api_layer_currency, encoder=encode_api_layer_currency, default=[]
    )
    currencies: list[AvailableCurrency] = fields.JSONField(
        default=default_currencies, decoder=decode_currencies, encoder=encode_currencies
    )
    preorder_time_alive: int = fields.IntField(default=60)  # noqa
    accounting_fee: float = fields.FloatField(default=0.95)  # noqa

    currency_wow: float = fields.FloatField(default=0.031)
    collect_currency_wow_by_sheets: bool = fields.BooleanField(default=False)  # noqa
    currency_wow_spreadsheet: str | None = fields.TextField(null=True)  # noqa
    currency_wow_sheet_id: int | None = fields.BigIntField(null=True)  # noqa
    currency_wow_cell: str | None = fields.TextField(null=True)  # noqa

    def get_precision(self, currency: str) -> int:
        for cur in self.currencies:
            if cur.name == currency:
                return cur.precision
        return 2


class SettingsRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    api_layer_currency: list[ApiLayerCurrencyToken]
    currencies: list[AvailableCurrency]
    preorder_time_alive: int
    accounting_fee: float

    currency_wow: float
    collect_currency_wow_by_sheets: bool
    currency_wow_spreadsheet: str | None
    currency_wow_sheet_id: int | None
    currency_wow_cell: str | None


class SettingsUpdate(BaseModel):
    preorder_time_alive: int | None = None
    accounting_precision_dollar: int | None = Field(ge=0, default=None)
    accounting_precision_rub: int | None = Field(ge=0, default=None)
    accounting_precision_gold: int | None = Field(ge=0, default=None)
    accounting_fee: float | None = Field(ge=0, le=1, default=None)
    currency_wow: float | None = Field(ge=0, default=None)
    collect_currency_wow_by_sheets: bool = Field(default=False)
    currency_wow_spreadsheet: str | None = Field(default=None)
    currency_wow_sheet_id: int | None = Field(default=None)
    currency_wow_cell: str | None = Field(default=None)
