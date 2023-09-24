from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, constr

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


class Settings(TimeStampMixin):
    api_layer_currency: list[ApiLayerCurrencyToken] = Field(default=[])
    currencies: list[AvailableCurrency] = Field(default=default_currencies)
    preorder_time_alive: int = 60
    accounting_fee: float = 0.95

    currency_wow: float = 0.031

    class Settings:
        name = "settings"
        use_state_management = True
        state_management_save_previous = True
        validate_on_save = True

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


class SettingsUpdate(BaseModel):
    preorder_time_alive: int | None = None

    accounting_precision_dollar: int | None = Field(ge=0, default=None)
    accounting_precision_rub: int | None = Field(ge=0, default=None)
    accounting_precision_gold: int | None = Field(ge=0, default=None)
    accounting_fee: float | None = Field(ge=0, le=1, default=None)
