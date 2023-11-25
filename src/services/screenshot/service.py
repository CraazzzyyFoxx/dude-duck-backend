import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status
from yarl import URL

from src.core import errors, pagination
from src.services.order import models as order_models

from . import models


async def get(session: AsyncSession, screenshot_id: int) -> models.Screenshot | None:
    query = (sa.select(models.Screenshot).where(models.Screenshot.id == screenshot_id).limit(1))
    result = await session.execute(query)
    return result.scalar_one_or_none()


async def get_by_order_id(session: AsyncSession, order_id: int) -> list[models.Screenshot]:
    query = (sa.select(models.Screenshot).where(models.Screenshot.order_id == order_id))
    result = await session.scalars(query)
    return result.all()  # type: ignore


async def create(
        session: AsyncSession, order: order_models.Order, screenshot_in: models.ScreenshotCreate
) -> models.Screenshot:
    url = URL(screenshot_in.url)
    model = models.Screenshot(
        order_id=order.id,
        source=url.host,
        url=screenshot_in.url,
    )
    session.add(model)
    await session.commit()
    return model


async def delete(session: AsyncSession, screenshot_id: int) -> models.Screenshot:
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
    await session.delete(screenshot)
    await session.commit()
    return screenshot
