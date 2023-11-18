from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, field_validator
from sqlalchemy import DateTime, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.core import db


class Currency(db.TimeStampMixin):
    __tablename__ = "currency"

    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), unique=True)
    timestamp: Mapped[int] = mapped_column(Integer())
    quotes: Mapped[dict[str, float]] = mapped_column(JSONB())


class CurrencyToken(db.TimeStampMixin):
    __tablename__ = "currency_token"

    token: Mapped[str] = mapped_column(String(), unique=True)
    uses: Mapped[int] = mapped_column(Integer(), default=1)
    last_use: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda x: datetime.now(UTC))


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
