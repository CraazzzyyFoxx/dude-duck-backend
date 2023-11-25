from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import BigInteger, Enum, Select, String
from sqlalchemy.orm import Mapped, mapped_column

from src.core import db, enums, pagination


class Channel(db.TimeStampMixin):
    __tablename__ = "integration_channel"

    game: Mapped[str] = mapped_column(String(), nullable=False)
    category: Mapped[str | None] = mapped_column(String(), nullable=True)
    integration: Mapped[enums.Integration] = mapped_column(Enum(enums.Integration))
    channel_id: Mapped[int] = mapped_column(BigInteger())


class ChannelCreate(BaseModel):
    game: str
    category: str | None = Field(default=None, min_length=1)
    integration: enums.Integration
    channel_id: int


class ChannelUpdate(BaseModel):
    game: str
    category: str | None = Field(default=None, min_length=1)
    integration: enums.Integration


class ChannelRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    game: str
    category: str | None
    channel_id: int
    integration: enums.Integration


class ChannelPaginationParams(pagination.PaginationParams):
    integration: enums.Integration
    game: str | None = None
    category: str | None = Field(default=None, min_length=1)

    def apply_filter(self, query: Select) -> Select:
        query = query.where(Channel.integration == self.integration)
        if self.game:
            query = query.where(Channel.game == self.game)
        if self.category:
            query = query.where(Channel.category == self.category)
        return query
