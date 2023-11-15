from enum import Enum
from typing import Generic, List, TypeVar

from pydantic import BaseModel, Field

__all__ = ("Paginated", "PaginationParams", )


SchemaType = TypeVar("SchemaType", bound=BaseModel)


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

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.per_page

    @property
    def limit(self) -> int:
        return self.per_page
