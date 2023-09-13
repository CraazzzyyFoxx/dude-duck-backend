from pydantic import BaseModel, Field


class ChannelCreate(BaseModel):
    game: str
    category: str | None = Field(default=None, min_length=1)
    channel_id: int


class ChannelUpdate(BaseModel):
    game: str
    category: str | None = Field(default=None, min_length=1)


class ChannelRead(BaseModel):
    id: int
    game: str
    category: str | None
    channel_id: int
