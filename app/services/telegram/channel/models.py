from beanie import PydanticObjectId
from pydantic import BaseModel, Field


class ChannelCreate(BaseModel):
    game: str
    category: str | None = Field(default=None, min_length=1)
    channel_id: int


class ChannelUpdate(BaseModel):
    game: str
    category: str | None = Field(default=None, min_length=1)


class ChannelRead(BaseModel):
    id: PydanticObjectId
    game: str
    category: str | None
    channel_id: int
