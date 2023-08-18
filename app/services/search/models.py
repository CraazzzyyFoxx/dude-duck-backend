from typing import Generic, List, TypeVar, TypedDict, Any
from enum import Enum

from pydantic import BaseModel, Field
from beanie.odm.enums import SortDirection

__all__ = ("Paginated", "PaginationParams", "SortingParams", "OrderSortingParams")


SchemaType = TypeVar("SchemaType", bound=BaseModel)


class PaginationDict(TypedDict):
    page: int
    per_page: int
    total: int
    results: List[Any]


class Paginated(BaseModel, Generic[SchemaType]):
    page: int
    per_page: int
    total: int
    results: List[SchemaType]


class PaginationParams(BaseModel):
    page: int = Field(1, ge=1)
    per_page: int = Field(10, ge=1, le=100)

    @property
    def skip(self) -> int:
        return (self.page - 1) * self.per_page

    @property
    def limit(self) -> int:
        return self.per_page


class SortOrder(Enum):
    ASC = "asc"
    DESC = "desc"

    def __int__(self) -> int:
        """Converts the enum to an integer to be used by MongoDB."""
        return 1 if self.value == "asc" else -1

    @property
    def direction(self) -> SortDirection:
        return SortDirection(int(self))


class OrderSelection(Enum):
    InProgress = "In Progress"
    Completed = "Completed"
    ALL = "ALL"


class SortingParams(BaseModel):
    sort: str = "created_at"
    order: SortOrder = SortOrder.ASC


class OrderSortingParams(SortingParams):
    completed: OrderSelection = OrderSelection.ALL
