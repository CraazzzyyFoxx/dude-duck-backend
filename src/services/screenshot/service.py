import re

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status
from yarl import URL

from src import models, schemas
from src.core import errors, pagination
from src.services.accounting import service as accounting_service

link_regex = re.compile(r"((https?):((//)|(\\\\))+([\w\d:#@%/;$()~_?\+-=\\\.&](#!)?)*)", re.DOTALL)


async def get(session: AsyncSession, screenshot_id: int) -> models.Screenshot | None:
    query = sa.select(models.Screenshot).where(models.Screenshot.id == screenshot_id).limit(1)
    result = await session.execute(query)
    return result.scalar_one_or_none()


async def get_by_order_id(session: AsyncSession, order_id: int) -> list[models.Screenshot]:
    query = sa.select(models.Screenshot).where(models.Screenshot.order_id == order_id)
    result = await session.scalars(query)
    return result.all()  # type: ignore


async def create(
    session: AsyncSession,
    user: models.User,
    order: models.Order,
    url: str,
) -> models.Screenshot:
    query = sa.select(models.Screenshot).where(models.Screenshot.url == url, models.Screenshot.order_id == order.id)
    result = await session.scalars(query)
    if result.one_or_none():
        raise errors.ApiHTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=[
                errors.ApiException(
                    msg=f"A screenshot with this url already exists. [url={url}, order_id={order.id}]",
                    code="not_access",
                )
            ],
        )
    url = URL(url)
    model = models.Screenshot(
        order_id=order.id,
        user_id=user.id,
        source=url.host,
        url=url.human_repr(),
    )
    session.add(model)
    await session.commit()
    return model


async def bulk_create(
    session: AsyncSession,
    user: models.User,
    order: models.Order,
    urls: list[str],
):
    screenshots: list[models.Screenshot] = []
    for raw_url in urls:
        url = URL(raw_url)
        if url.human_repr() in [screenshot.url for screenshot in screenshots]:
            continue
        model = models.Screenshot(
            order_id=order.id,
            user_id=user.id,
            source=url.host,
            url=url.human_repr(),
        )
        screenshots.append(model)
    session.add_all(screenshots)
    await session.commit()
    return screenshots


async def delete(session: AsyncSession, user: models.User, screenshot: models.Screenshot) -> models.Screenshot:
    if not screenshot:
        raise errors.ApiHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[
                errors.ApiException(
                    msg=f"A screenshot with this id does not exist. [screenshot={screenshot}]",
                    code="not_exist",
                )
            ],
        )

    if not user.is_superuser:
        order_id = screenshot.order_id
        user_order = await accounting_service.get_by_order_id_user_id(session, order_id, user.id)
        if not user_order:
            raise errors.ApiHTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=[
                    errors.ApiException(
                        msg=f"User does not have access to this order. [user_id={user.id}, order_id={order_id}]",
                        code="not_access",
                    )
                ],
            )

    await session.delete(screenshot)
    await session.commit()
    return screenshot


async def get_by_filter(session: AsyncSession, params: schemas.ScreenshotParams):
    query = params.apply_filters(sa.select(models.Screenshot))
    result = await session.scalars(params.apply_pagination(query))
    total = await session.execute(params.apply_filters(sa.select(sa.func.count(models.Screenshot.id))))
    results = [schemas.ScreenshotRead.model_validate(row, from_attributes=True) for row in result.all()]
    return pagination.Paginated(
        results=results,
        total=total.scalar_one(),
        page=params.page,
        per_page=params.per_page,
    )


def find_url_in_text(text: str) -> list[str]:
    return [URL(match[0]).human_repr() for match in link_regex.findall(text) if match[0] is not None]
