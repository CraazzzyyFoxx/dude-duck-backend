from datetime import datetime, timedelta

from beanie import Document
from pydantic import BaseModel, field_validator
from pymongo import IndexModel


class Currency(Document):
    date: datetime
    timestamp: int

    quotes: dict[str, float]

    class Settings:
        use_cache = True
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
    def date_validator(cls, v: str):
        return datetime.strptime(v, "%Y-%m-%d")
