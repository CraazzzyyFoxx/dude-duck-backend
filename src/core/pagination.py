from enum import Enum
from typing import Generic, List, TypedDict, TypeVar

from pydantic import BaseModel, Field
from sqlalchemy import Select, text

from . import db

__all__ = (
    "Paginated",
    "PaginationParams",
)


SchemaType = TypeVar("SchemaType", bound=BaseModel)
ModelType = TypeVar("ModelType", bound=db.TimeStampMixin)


class PaginationDict(TypedDict, Generic[ModelType]):
    page: int
    per_page: int
    total: int
    results: List[ModelType]


class Paginated(BaseModel, Generic[SchemaType]):
    page: int
    per_page: int
    total: int
    results: List[SchemaType]


class SortOrder(Enum):
    ASC = "asc"
    DESC = "desc"


class PaginationParams(BaseModel):
    page: int = Field(1, ge=1)
    per_page: int = Field(10, ge=1, le=100)
    sort: str = "created_at"
    order: SortOrder = SortOrder.ASC

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.per_page

    @property
    def limit(self) -> int:
        return self.per_page

    @property
    def order_by(self):
        order_by = " DESC" if self.order == SortOrder.DESC else ""
        return text(f"{self.sort}{order_by}")

    def apply_pagination(self, query: Select) -> Select:
        return query.offset(self.offset).limit(self.limit).order_by(self.order_by)
