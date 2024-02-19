from datetime import UTC, datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.core import db

__all__ = ("Currency", "CurrencyToken", )


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
