from fastapi import HTTPException
from starlette import status
from beanie import PydanticObjectId, init_beanie

from app import db
from app.core import config
from app.services.auth import service as auth_service
from app.services.sheets import service as sheets_service
from app.services.tasks import service as tasks_service
from app.services.settings import service as settings_service
from app.services.telegram.message import service as message_service
from app.services.permissions import service as permissions_service

from . import service, models


async def get(
        order_id: PydanticObjectId
) -> models.PreOrder:
    order = await service.get(order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[{"msg": "A preorder with this id does not exist."}],
        )
    return order


async def get_order_id(
        order_id: str
) -> models.PreOrder:
    order = await service.get_order_id(order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[{"msg": "A preorder with this id does not exist."}],
        )
    return order


async def create(
        order_in: models.PreOrderCreate
) -> models.PreOrder:
    order = await service.create(order_in)
    settings = await settings_service.get()
    tasks_service.delete_expired_preorder.apply_async((str(order.id), ), countdown=settings.preorder_time_alive)
    return order


async def delete(
        order_id: PydanticObjectId
):
    await init_beanie(connection_string=config.app.mongo_dsn, document_models=db.get_beanie_models())
    order = await service.get(PydanticObjectId(order_id))
    if not order:
        return
    parser = await sheets_service.get_by_spreadsheet_sheet(order.spreadsheet, order.sheet_id)
    parser = sheets_service.models.OrderSheetParseRead.model_validate(parser.model_dump())
    creds = await auth_service.get_first_superuser()
    sheets_service.clear_row(creds.google, parser, order.row_id)
    await service.to_archive(order.id)
    await message_service.pull_preorder_delete(await permissions_service.format_preorder(order))
