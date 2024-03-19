from datetime import UTC, datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.core import db

__all__ = ("Currency", )


class Currency(db.TimeStampMixin):
    __tablename__ = "currency"

    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), unique=True)
    timestamp: Mapped[int] = mapped_column(Integer())
    quotes: Mapped[dict[str, float]] = mapped_column(JSONB())
