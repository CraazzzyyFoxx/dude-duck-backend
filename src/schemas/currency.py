from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator


__all__ = ("CurrencyTokenRead", "CurrencyApiLayer", "CurrencyAPI", "CurrencyMetaAPI", "CurrencyEntityAPI")


class CurrencyTokenRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    token: str
    uses: int
    last_use: datetime


class CurrencyApiLayer(BaseModel):
    success: bool
    historical: bool
    date: datetime
    timestamp: int
    source: str

    quotes: dict[str, float]

    def normalize_quotes(self) -> dict[str, float]:
        data = {}
        for name, value in self.quotes.items():
            name = name.replace(self.source.upper(), "")
            data[name] = value
        return data

    @field_validator("date", mode="before")
    def date_validator(cls, v: str) -> datetime:
        return datetime.strptime(v, "%Y-%m-%d")


class CurrencyMetaAPI(BaseModel):
    last_updated_at: datetime


class CurrencyEntityAPI(BaseModel):
    code: str
    value: float


class CurrencyAPI(BaseModel):
    meta: CurrencyMetaAPI
    data: dict[str, CurrencyEntityAPI]

    def normalize_quotes(self) -> dict[str, float]:
        data = {}
        for name, value in self.data.items():
            data[value.code] = value.value
        return data
