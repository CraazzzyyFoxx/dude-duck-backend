from datetime import datetime, timedelta

import pytz
import sqlalchemy as sa
from loguru import logger

from src import models
from src.core import db, enums
from src.services.integrations.message import service as message_service
from src.services.integrations.notifications import \
    flows as notifications_flows
from src.services.integrations.sheets import service as sheets_service
from src.services.order import service as order_service
from src.services.settings import service as settings_service

from . import service


async def manage_preorders():
    async with db.async_session_maker() as session:
        creds = await sheets_service.get_first_superuser_token(session)
        settings = await settings_service.get(session)
        if creds is None:
            logger.warning("Manage preorders skipped, google token for first superuser missing")
            return

        preorders = await service.get_all(session)
        for preorder in preorders:
            order = await order_service.get_order_id(session, preorder.order_id)
            delta = (datetime.utcnow() - timedelta(seconds=settings.preorder_time_alive)).astimezone(pytz.UTC)
            if preorder.created_at < delta:
                query = sa.delete(models.PreOrder).where(models.PreOrder.id == preorder.id)
                await session.execute(query)
                for member in enums.Integration:
                    integration = enums.Integration(member)
                    payload = await message_service.delete_order_message(
                        session,
                        models.DeleteOrderMessage(
                            order_id=preorder.id,
                            integration=integration,
                            is_preorder=True,
                        ),
                    )
                if payload.deleted:
                    notifications_flows.send_deleted_order_notify(preorder.order_id, payload)
                if preorder.has_response is False and order is None:
                    parser = await sheets_service.get_by_spreadsheet_sheet_read(
                        session, preorder.spreadsheet, preorder.sheet_id
                    )
                    sheets_service.clear_row(creds.token, parser, preorder.row_id)
        await session.commit()
