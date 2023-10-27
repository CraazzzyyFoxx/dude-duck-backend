from datetime import datetime

from pydantic import BaseModel, field_validator
from sqlalchemy import DateTime, Integer
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.core import db


class Currency(db.TimeStampMixin):
    __tablename__ = "currency"

    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), unique=True)
    timestamp: Mapped[int] = mapped_column(Integer())
    quotes: Mapped[dict[str, float]] = mapped_column(JSONB())


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
