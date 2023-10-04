import copy
from datetime import datetime

from loguru import logger

from app.services.accounting import service as accounting_service
from app.services.auth import service as auth_service
from app.services.sheets import flows as sheets_flows
from app.services.tasks import service as tasks_service

from . import models


async def get(order_id: int, prefetch: bool = True) -> models.Order | None:
    query = models.Order.filter(id=order_id)
    if prefetch:
        query = query.prefetch_related("info", "price", "credentials")
    return await query.first()


async def get_all() -> list[models.Order]:
    return await models.Order.all().prefetch_related("info", "price", "credentials")


async def get_all_by_sheet(spreadsheet: str, sheet: int, prefetch: bool = True) -> list[models.Order]:
    query = models.Order.filter(spreadsheet=spreadsheet, sheet_id=sheet)
    if prefetch:
        query = query.prefetch_related("info", "price", "credentials")
    return await query


async def get_all_by_sheet_entity(spreadsheet: str, sheet: int, row_id: int) -> list[models.Order]:
    return await models.Order.filter(spreadsheet=spreadsheet, sheet_id=sheet, row_id=row_id).prefetch_related(
        "info", "price", "credentials"
    )


async def get_order_id(order_id: str) -> models.Order | None:
    return await models.Order.filter(order_id=order_id).prefetch_related("info", "price", "credentials").first()


async def get_all_from_datetime_range(start: datetime, end: datetime) -> list[models.Order]:
    return await models.Order.filter(date__gte=start, date__lte=end).prefetch_related("info", "price", "credentials")


async def get_by_ids(ids: list[int], prefetch: bool = True) -> list[models.Order]:
    query = models.Order.filter(id__in=ids)
    if prefetch:
        query = query.prefetch_related("info", "price", "credentials")
    return await query


async def get_by_ids_datetime_range(ids: list[int], start: datetime, end: datetime) -> list[models.Order]:
    return await models.Order.filter(id__in=ids, date__gte=start, date__lte=end).prefetch_related(
        "info", "price", "credentials"
    )


async def get_by_ids_datetime_range_by_sheet(
    ids: list[int], spreadsheet: str, sheet: int, start: datetime, end: datetime
) -> list[models.Order]:
    return await models.Order.filter(
        spreadsheet=spreadsheet,
        sheet_id=sheet,
        id__in=ids,
        date__gte=start,
        date__lte=end,
    ).prefetch_related("info", "price", "credentials")


async def get_all_from_datetime_range_by_sheet(
    spreadsheet: str, sheet: int, start: datetime, end: datetime
) -> list[models.Order]:
    return await models.Order.filter(
        spreadsheet=spreadsheet, sheet_id=sheet, date__gte=start, date__lte=end
    ).prefetch_related("info", "price", "credentials")


async def update_with_sync(order: models.Order, order_in: models.OrderUpdate) -> models.Order:
    order = await patch(order, order_in)
    parser = await sheets_flows.service.get_by_spreadsheet_sheet_read(order.spreadsheet, order.sheet_id)
    user = await auth_service.get_first_superuser()
    tasks_service.update_order.delay(
        user.google.model_dump_json(), parser.model_dump_json(), order.row_id, order_in.model_dump()
    )

    return order


async def patch(order: models.Order, order_in: models.OrderUpdate) -> models.Order:
    await order.fetch_related("price", "info", "credentials")
    old = copy.deepcopy(order)
    update_data = order_in.model_dump(
        exclude_defaults=True, exclude_unset=True, exclude={"price", "info", "credentials"}
    )
    order = await order.update_from_dict(update_data)
    if order_in.info:
        info_update = order_in.info.model_dump(exclude_defaults=True, exclude_unset=True)
        await order.info.update_from_dict(info_update)
        await order.info.save(update_fields=info_update.keys())
    if order_in.credentials:
        credentials_update = order_in.credentials.model_dump(exclude_defaults=True, exclude_unset=True)
        await order.credentials.update_from_dict(credentials_update)
        await order.credentials.save(update_fields=credentials_update.keys())
    if order_in.price:
        price_update = order_in.price.model_dump(exclude_defaults=True, exclude_unset=True)
        await order.price.update_from_dict(price_update)
        await order.price.save(update_fields=price_update.keys())
        await accounting_service.update_booster_price(old, order)
    await order.save(update_fields=update_data.keys())
    logger.info(f"Order patched [id={order.id} order_id={order.order_id}]]")
    return order


async def update(order: models.Order, order_in: models.OrderUpdate) -> models.Order:
    await order.fetch_related("price", "info", "credentials")
    old = copy.deepcopy(order)
    update_data = order_in.model_dump(exclude={"price", "info", "credentials"})
    order = await order.update_from_dict(update_data)
    await order.info.update_from_dict(order_in.info.model_dump(exclude_defaults=True))
    await order.info.save()
    await order.credentials.update_from_dict(order_in.price.model_dump(exclude_defaults=True))
    await order.credentials.save()
    update_data_price = order_in.price.model_dump(exclude_defaults=True)
    if update_data_price:
        await order.price.update_from_dict(update_data_price)
        await order.price.save()
        await accounting_service.update_booster_price(old, order)
    await order.save()

    if order.status == models.OrderStatus.Refund:
        await accounting_service.delete_by_order_id(order.id)

    logger.info(f"Order updated [id={order.id} order_id={order.order_id}]]")
    return order


async def delete(order_id: int) -> None:
    order = await get(order_id)
    logger.info(f"Order deleted [id={order.id} order_id={order.order_id}]]")


async def create(order_in: models.OrderCreate) -> models.Order:
    order = await models.Order.create(**order_in.model_dump(exclude={"price", "info", "credentials"}))
    await models.OrderInfo.create(**order_in.info.model_dump(), order_id=order.id)
    await models.OrderPrice.create(**order_in.price.model_dump(), order_id=order.id)
    await models.OrderCredentials.create(**order_in.credentials.model_dump(), order_id=order.id)
    logger.info(f"Order created [id={order.id} order_id={order.order_id}]]")
    return await get(order.id, prefetch=True)
