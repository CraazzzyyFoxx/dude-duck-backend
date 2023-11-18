from datetime import datetime, timedelta

import pytz
from loguru import logger

from src.core import db
from src.services.auth import service as auth_service
from src.services.order import service as order_service
from src.services.settings import service as settings_service
from src.services.sheets import service as sheets_service
from src.services.telegram.message import service as message_service

from . import flows, service


async def manage_preorders():
    async with db.async_session_maker() as session:
        superuser = await auth_service.get_first_superuser(session)
        settings = await settings_service.get(session)
        if superuser.google is None:
            logger.warning("Manage preorders skipped, google token for first superuser missing")
            return

        preorders = await service.get_all(session)
        for preorder in preorders:
            order = await order_service.get_order_id(session, preorder.order_id)
            delta = (datetime.utcnow() - timedelta(seconds=settings.preorder_time_alive)).astimezone(pytz.UTC)
            if preorder.created_at < delta:
                session.delete(preorder)
                payload = await message_service.order_delete(await flows.format_preorder_system(preorder), pre=True)
                if payload.deleted:
                    message_service.send_deleted_order_notify(preorder.order_id, payload)
                if preorder.has_response is False and order is None:
                    parser = await sheets_service.get_by_spreadsheet_sheet_read(preorder.spreadsheet, preorder.sheet_id)
                    sheets_service.clear_row(superuser.google, parser, preorder.row_id)
