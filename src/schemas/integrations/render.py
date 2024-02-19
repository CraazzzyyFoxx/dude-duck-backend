from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Select


from src.core import enums, pagination

__all__ = ("RenderConfigCreate", "RenderConfigUpdate", "RenderConfigRead", "RenderConfigParams")

from src.models.integrations.render import RenderConfig


class RenderConfigCreate(BaseModel):
    name: str
    integration: enums.Integration
    lang: str = Field(default="en")
    binary: str
    allow_separator_top: bool = Field(default=True)
    separator: str = Field(default="▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬")


class RenderConfigUpdate(BaseModel):
    binary: str | None = None
    allow_separator_top: bool | None = None
    separator: str | None = None


class RenderConfigRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    integration: enums.Integration
    lang: str
    binary: str
    allow_separator_top: bool
    separator: str


class RenderConfigParams(pagination.PaginationParams):
    names: list[str] | None = None
    allow_separator_top: bool | None = None
    separator: str | None = None
    integration: enums.Integration | None = None

    def apply_filter(self, query: Select) -> Select:
        if self.names:
            query = query.where(RenderConfig.name.in_(self.names))
        if self.allow_separator_top is not None:
            query = query.where(RenderConfig.allow_separator_top == self.allow_separator_top)
        if self.separator:
            query = query.where(RenderConfig.separator == self.separator)
        if self.integration:
            query = query.where(RenderConfig.integration == self.integration)
        return query
