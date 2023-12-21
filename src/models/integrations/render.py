from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Boolean, Enum, Select, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.core import db, enums, pagination

__all__ = ("RenderConfig", "RenderConfigCreate", "RenderConfigUpdate", "RenderConfigRead", "RenderConfigParams")


class RenderConfig(db.TimeStampMixin):
    __tablename__ = "integration_render_config"
    __table_args__ = (UniqueConstraint("name", "lang", "integration", name="idx_name_lang"),)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    lang: Mapped[str] = mapped_column(String(255), nullable=False)
    integration: Mapped[enums.Integration] = mapped_column(Enum(enums.Integration), nullable=False)
    binary: Mapped[str] = mapped_column(Text(), nullable=False)
    allow_separator_top: Mapped[bool] = mapped_column(Boolean, nullable=False)
    separator: Mapped[str] = mapped_column(String(255), nullable=False)


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
