from sqlalchemy import BigInteger, Enum,  String
from sqlalchemy.orm import Mapped, mapped_column

from src.core import db, enums

__all__ = ("Channel", )


class Channel(db.TimeStampMixin):
    __tablename__ = "integration_channel"

    game: Mapped[str] = mapped_column(String(), nullable=False)
    category: Mapped[str | None] = mapped_column(String(), nullable=True)
    integration: Mapped[enums.Integration] = mapped_column(Enum(enums.Integration))
    channel_id: Mapped[int] = mapped_column(BigInteger())
