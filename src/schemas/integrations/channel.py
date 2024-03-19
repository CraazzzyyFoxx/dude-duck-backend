from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Select

from src import models
from src.core import enums, pagination

__all__ = ("ChannelCreate", "ChannelUpdate", "ChannelRead", "ChannelPaginationParams")


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
        query = query.where(models.Channel.integration == self.integration)
        if self.game:
            query = query.where(models.Channel.game == self.game)
        if self.category:
            query = query.where(models.Channel.category == self.category)
        return query
