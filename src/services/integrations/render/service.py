import sqlalchemy as sa
from cashews import cache
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from src import models, schemas
from src.core import enums, errors, pagination


def get_all_config_names(
    order: schemas.OrderReadSystem | models.PreOrderReadSystem,
) -> list[str]:
    return [
        "order",
        "eta-price",
        "eta-price-gold",
        "response",
        "response-check",
        order.info.game,
        f"{order.info.game}-cd",
        "pre-order",
        "pre-eta-price",
        "pre-eta-price-gold",
    ]


async def get(session: AsyncSession, config_id: int) -> models.RenderConfig | None:
    query = sa.select(models.RenderConfig).where(models.RenderConfig.id == config_id)
    result = await session.execute(query)
    return result.scalars().first()


async def create(session: AsyncSession, config_in: models.RenderConfigCreate) -> models.RenderConfig:
    model = models.RenderConfig(**config_in.model_dump())
    session.add(model)
    await session.commit()
    return model


@cache.invalidate("render_config_*")
async def delete(session: AsyncSession, config_id: int) -> models.RenderConfig:
    config = await get(session, config_id)
    if not config:
        raise errors.ApiHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[
                errors.ApiException(
                    msg=f"Render Config with id={config_id} not found.",
                    code="not_found",
                )
            ],
        )
    await session.delete(config)
    await session.commit()
    return config


@cache.cache(ttl=3600, key="render_config_{integration}_{name}")
async def get_by_name(session: AsyncSession, integration: enums.Integration, name: str) -> models.RenderConfig | None:
    query = sa.select(models.RenderConfig).where(
        models.RenderConfig.name == name, models.RenderConfig.integration == integration
    )
    result = await session.execute(query)
    return result.scalars().first()


async def get_by_names(
    session: AsyncSession, integration: enums.Integration, names: list[str]
) -> list[models.RenderConfig]:
    query = (
        sa.select(models.RenderConfig)
        .where(models.RenderConfig.name.in_(names))
        .where(models.RenderConfig.integration == integration)
    )
    result = await session.execute(query)
    return result.scalars().all()  # type: ignore


@cache.invalidate("render_config_{parser.integration}_{parser.name}")
async def update(
    session: AsyncSession,
    parser: models.RenderConfig,
    parser_in: models.RenderConfigUpdate,
) -> models.RenderConfig:
    update_data = parser_in.model_dump(exclude_none=True)
    for key, value in update_data.items():
        setattr(parser, key, value)

    session.add(parser)
    await session.commit()
    return parser


async def get_all_configs_for_order(
    session: AsyncSession,
    integration: enums.Integration,
    order: schemas.OrderReadSystem | models.PreOrderReadSystem,
) -> list[models.RenderConfig]:
    names = get_all_config_names(order)
    return await get_by_names(session, integration, names)


async def get_by_filter(
    session: AsyncSession, params: models.RenderConfigParams
) -> pagination.Paginated[models.RenderConfigRead]:
    query = sa.select(models.RenderConfig)
    query = params.apply_pagination(query)
    query = params.apply_filter(query)
    result = await session.execute(query)
    total = await session.execute(params.apply_filter(sa.select(sa.func.count(models.RenderConfig.id))))
    results = [models.RenderConfigRead.model_validate(item, from_attributes=True) for item in result.scalars().all()]
    return pagination.Paginated(
        results=results,
        total=total.scalar_one(),
        page=params.page,
        per_page=params.per_page,
    )
