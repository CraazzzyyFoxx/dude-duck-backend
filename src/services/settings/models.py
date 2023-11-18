import typing

from pydantic import BaseModel, ConfigDict, Field, StringConstraints
from sqlalchemy import BigInteger, Boolean, Float, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.core import db


class AvailableCurrency(BaseModel):
    name: typing.Annotated[str, StringConstraints(to_upper=True)]
    precision: int


class AvailableCurrencyDB(typing.TypedDict):
    name: str
    precision: int


default_currencies = [
    AvailableCurrency(name="USD", precision=2),
    AvailableCurrency(name="RUB", precision=0),
    AvailableCurrency(name="WOW", precision=0),
]
default_currencies_dict = [c.model_dump() for c in default_currencies]


class Settings(db.TimeStampMixin):
    __tablename__ = "settings"

    currencies: Mapped[list[AvailableCurrencyDB]] = mapped_column(JSONB(), default=default_currencies_dict)
    preorder_time_alive: Mapped[int] = mapped_column(Integer(), default=60)
    accounting_fee: Mapped[float] = mapped_column(Float(), default=0.95)

    currency_wow: Mapped[float] = mapped_column(Float(), default=0.031)
    collect_currency_wow_by_sheets: Mapped[bool] = mapped_column(Boolean(), default=False)
    currency_wow_spreadsheet: Mapped[str | None] = mapped_column(String(), nullable=True)
    currency_wow_sheet_id: Mapped[int | None] = mapped_column(BigInteger(), nullable=True)
    currency_wow_cell: Mapped[str | None] = mapped_column(String(), nullable=True)

    def get_precision(self, currency: str) -> int:
        for cur in self.currencies:
            if cur["name"] == currency:
                return cur["precision"]
        return 2


class SettingsRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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
