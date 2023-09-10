from beanie import PydanticObjectId
from pydantic import BaseModel, Field


class RenderConfigCreate(BaseModel):
    name: str
    lang: str = Field(default="en")
    binary: str
    allow_separator_top: bool = Field(default=True)
    separator: str = Field(default="▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬")


class RenderConfigUpdate(BaseModel):
    binary: str | None = None
    allow_separator_top: bool | None = None
    separator: str | None = None


class RenderConfigRead(BaseModel):
    id: PydanticObjectId
    name: str
    lang: str
    binary: str
    allow_separator_top: bool
    separator: str
