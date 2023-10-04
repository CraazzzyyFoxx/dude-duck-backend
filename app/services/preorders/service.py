from loguru import logger

from . import models


async def get(order_id: int) -> models.PreOrder | None:
    return await models.PreOrder.filter(id=order_id).prefetch_related("price", "info").first()


async def get_all() -> list[models.PreOrder]:
    return await models.PreOrder.all().prefetch_related("price", "info")


async def get_all_by_sheet(spreadsheet: str, sheet: int) -> list[models.PreOrder]:
    return await models.PreOrder.filter(spreadsheet=spreadsheet, sheet_id=sheet).prefetch_related("price", "info")


async def get_all_by_sheet_entity(spreadsheet: str, sheet: int, row_id: int) -> list[models.PreOrder]:
    return await models.PreOrder.filter(spreadsheet=spreadsheet, sheet_id=sheet, row_id=row_id).prefetch_related(
        "price", "info"
    )


async def get_order_id(order_id: str) -> models.PreOrder | None:
    return await models.PreOrder.filter(order_id=order_id).prefetch_related("price", "info").first()


async def patch(order: models.PreOrder, order_in: models.PreOrderUpdate) -> models.PreOrder:
    await order.fetch_related("price", "info", "credentials")
    update_data = order_in.model_dump(
        exclude_defaults=True, exclude_unset=True, exclude={"price", "info", "credentials"}
    )
    order = await order.update_from_dict(update_data)
    if order_in.info:
        info_update = order_in.info.model_dump(exclude_defaults=True, exclude_unset=True)
        await order.info.update_from_dict(info_update)
        await order.info.save(update_fields=info_update.keys())
    if order_in.price:
        price_update = order_in.price.model_dump(exclude_defaults=True, exclude_unset=True)
        await order.price.update_from_dict(price_update)
        await order.price.save(update_fields=price_update.keys())
    await order.save(update_fields=update_data.keys())
    logger.info(f"Order patched [id={order.id} order_id={order.order_id}]]")
    return order


async def update(order: models.PreOrder, order_in: models.PreOrderUpdate) -> models.PreOrder:
    await order.fetch_related("price", "info", "credentials")
    update_data = order_in.model_dump(exclude={"price", "info", "credentials"})
    order = await order.update_from_dict(update_data)
    await order.info.update_from_dict(order_in.info.model_dump(exclude_defaults=True))
    await order.info.save()
    await order.price.update_from_dict(order_in.price.model_dump(exclude_defaults=True))
    await order.price.save()
    await order.save()
    logger.info(f"Order updated [id={order.id} order_id={order.order_id}]]")
    return order


async def create(pre_order_in: models.PreOrderCreate) -> models.PreOrder:
    pre_order = await models.PreOrder.create(**pre_order_in.model_dump(exclude={"price", "info", "credentials"}))
    await models.PreOrderInfo.create(**pre_order_in.info.model_dump(), order_id=pre_order.id)
    await models.PreOrderPrice.create(**pre_order_in.price.model_dump(), order_id=pre_order.id)
    logger.info(f"PreOrder created [id={pre_order.id} order_id={pre_order.order_id}]]")
    return await get(pre_order.id)


async def delete(order_id: int):
    order = await get(order_id)
    if order:
        await order.delete()
