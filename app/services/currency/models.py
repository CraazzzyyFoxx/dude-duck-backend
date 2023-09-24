from datetime import datetime, timedelta

from pydantic import BaseModel, field_validator
from pymongo import IndexModel

from app.core.db import TimeStampMixin


class Currency(TimeStampMixin):
    date: datetime
    timestamp: int

    quotes: dict[str, float]

    class Settings:
        name = "currency"
        use_cache = True
        validate_on_save = True
        cache_expiration_time = timedelta(days=1)
        cache_capacity = 100

        indexes = [
            IndexModel(["date"], unique=True),
        ]


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
