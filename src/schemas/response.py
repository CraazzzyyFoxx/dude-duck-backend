from datetime import datetime, timedelta

from pydantic import BaseModel, ConfigDict
from sqlalchemy import Select

from src.core import pagination

__all__ = ("ResponseExtra", "ResponseCreate", "ResponseRead", "ResponseUpdate", "Response", "ResponsePagination")

from src.models import Response


class ResponseExtra(BaseModel):
    text: str | None = None
    price: float | None = None
    start_date: datetime | None = None
    eta: timedelta | None = None


class ResponseCreate(BaseModel):
    order_id: int
    user_id: int

    text: str | None = None
    price: float | None = None
    start_date: datetime | None = None
    eta: timedelta | None = None


class ResponseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    order_id: int
    user_id: int

    refund: bool
    approved: bool
    closed: bool

    text: str | None
    price: float | None
    start_date: datetime | None
    eta: timedelta | None


class ResponseUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    refund: bool | None = None
    approved: bool
    closed: bool


class ResponsePagination(pagination.PaginationParams):
    order_id: int | None = None
    user_id: int | None = None
    is_preorder: bool | None = None

    def apply_filter(self, query: Select) -> Select:
        if self.order_id is not None:
            query = query.where(Response.order_id == self.order_id)
        if self.user_id is not None:
            query = query.where(Response.user_id == self.user_id)
        if self.is_preorder is not None:
            query = query.where(Response.is_preorder == self.is_preorder)
        return query
