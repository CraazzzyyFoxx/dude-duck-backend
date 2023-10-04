from enum import Enum
from typing import Generic, List, TypedDict, TypeVar

from pydantic import BaseModel, Field
from tortoise.models import Model

__all__ = ("Paginated", "PaginationParams", "SortingParams", "OrderSortingParams")


SchemaType = TypeVar("SchemaType", bound=BaseModel)
ModelType = TypeVar("ModelType", bound=Model)


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

    @property
    def direction(self) -> str:
        return "-" if self.value == "asc" else "+"


class OrderSelection(Enum):
    InProgress = "In Progress"
    Completed = "Completed"
    ALL = "ALL"


class SortingParams(BaseModel):
    sort: str = "created_at"
    order: SortOrder = SortOrder.ASC

    @property
    def order_by(self):
        order_by = "-" if self.order == SortOrder.DESC else ""
        return f"{order_by}{self.sort}"


class OrderSortingParams(SortingParams):
    completed: OrderSelection = OrderSelection.ALL
