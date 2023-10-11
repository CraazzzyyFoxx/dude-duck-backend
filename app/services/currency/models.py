from datetime import datetime

from pydantic import BaseModel, field_validator
from tortoise import fields

from app.core.db import TimeStampMixin


class Currency(TimeStampMixin):
    date: datetime = fields.DatetimeField(unique=True)
    timestamp: int = fields.IntField()
    quotes: dict[str, float] = fields.JSONField()

    class Meta:
        name = "currency"


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
