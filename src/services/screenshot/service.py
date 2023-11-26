import re

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status
from yarl import URL

from src.core import errors, pagination
from src.services.accounting import service as accounting_service
from src.services.auth import models as auth_models
from src.services.order import models as order_models
from src.services.order import schemas as order_schemas

link_regex = re.compile(r"((https?):((//)|(\\\\))+([\w\d:#@%/;$()~_?\+-=\\\.&](#!)?)*)", re.DOTALL)


async def get(session: AsyncSession, screenshot_id: int) -> order_models.Screenshot | None:
    query = sa.select(order_models.Screenshot).where(order_models.Screenshot.id == screenshot_id).limit(1)
    result = await session.execute(query)
    return result.scalar_one_or_none()


async def get_by_order_id(session: AsyncSession, order_id: int) -> list[order_models.Screenshot]:
    query = sa.select(order_models.Screenshot).where(order_models.Screenshot.order_id == order_id)
    result = await session.scalars(query)
    return result.all()  # type: ignore


async def create(
    session: AsyncSession,
    user: auth_models.User,
    order: order_models.Order,
    url: str,
) -> order_models.Screenshot:
    query = sa.select(order_models.Screenshot).where(
        order_models.Screenshot.url == url, order_models.Screenshot.order_id == order.id
    )
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
    if not user.is_superuser:  # TODO: Move it to flows
        user_order = await accounting_service.get_by_order_id_user_id(session, order.id, user.id)
        if not user_order:
            raise errors.ApiHTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=[
                    errors.ApiException(
                        msg=f"User does not have access to this order. [user_id={user.id}, order_id={order.id}]",
                        code="already_exist",
                    )
                ],
            )
    url = URL(url)
    model = order_models.Screenshot(
        order_id=order.id,
        user_id=user.id,
        source=url.host,
        url=url.human_repr(),
    )
    session.add(model)
    await session.commit()
    return model


async def bulk_create(session: AsyncSession, user: auth_models.User, order: order_models.Order, urls: list[str]):
    screenshots: list[order_models.Screenshot] = []
    for raw_url in urls:
        url = URL(raw_url)
        if url.human_repr() in [screenshot.url for screenshot in screenshots]:
            continue
        model = order_models.Screenshot(
            order_id=order.id,
            user_id=user.id,
            source=url.host,
            url=url.human_repr(),
        )
        screenshots.append(model)
    session.add_all(screenshots)
    await session.commit()
    return screenshots


async def delete(session: AsyncSession, user: auth_models.User, screenshot_id: int) -> order_models.Screenshot:
    screenshot = await get(session, screenshot_id)
    if not screenshot:
        raise errors.ApiHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[
                errors.ApiException(
                    msg=f"A screenshot with this id does not exist. [screenshot={screenshot}]", code="not_exist"
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


async def get_by_filter(session: AsyncSession, params: order_schemas.ScreenshotParams):
    query = params.apply_filters(sa.select(order_models.Screenshot))
    result = await session.scalars(params.apply_pagination(query))
    total = await session.execute(params.apply_filters(sa.select(sa.func.count())))
    results = [order_models.ScreenshotRead.model_validate(row, from_attributes=True) for row in result.all()]
    return pagination.Paginated(results=results, total=total.scalar_one(), page=params.page, per_page=params.per_page)


def find_url_in_text(text: str) -> list[str]:
    return [URL(match[0]).human_repr() for match in link_regex.findall(text) if match[0] is not None]
