from typing import TypeVar

from beanie import Document
from beanie.odm.queries.find import FindMany
from tortoise.queryset import QuerySet

from . import models

DocumentType = TypeVar("DocumentType", bound=Document)


async def paginate(
    query: QuerySet,
    paging_params: models.PaginationParams,
    sorting_params: models.SortingParams,
) -> models.PaginationDict:
    total = await query.count()
    results = await query.offset(paging_params.skip).limit(paging_params.limit).order_by(sorting_params.order_by)
    return {
        "page": paging_params.page,
        "per_page": paging_params.per_page,
        "total": total,
        "results": results,
    }
