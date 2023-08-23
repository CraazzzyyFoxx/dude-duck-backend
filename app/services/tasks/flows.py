import time
from typing import cast

from loguru import logger
from deepdiff import DeepDiff


from app.services.orders import service as order_service
from app.services.sheets import flows as sheets_flows
from app.services.sheets import service as sheets_service
from app.services.accounting import service as accounting_service
from app.services.auth import service as auth_service

from .service import loop


async def sync_data_from(
        cfg: sheets_flows.models.OrderSheetParse,
        orders: dict[str, sheets_flows.models.OrderReadSheets]
):
    t = time.time()
    orders_db = await order_service.get_all_by_sheet(cfg.spreadsheet, cfg.sheet_id)
    users = await auth_service.models.User.find_all().to_list()
    for order in orders_db:
        s_order = orders.get(order.order_id, None)
        if s_order is None:
            await order_service.to_archive(order.id)
        else:
            orders.pop(s_order.order_id)
            changes = DeepDiff(order.model_dump(exclude={'id', "revision_id", "archive"}),
                               s_order.model_dump(exclude={'id', "revision_id"}))
            if changes:
                s_order.booster = None
                await order_service.update(order, s_order)
    for order_s in orders.values():
        order = await order_service.create(order_s)
        await accounting_service.boosters_from_order_sync(order, users)

    logger.info(f"Syncing data from sheet[spreadsheet={cfg.spreadsheet} sheet_id={cfg.sheet_id}] "
                f"completed in {time.time() - t}")


async def sync_data_to(cfg: sheets_flows.models.OrderSheetParse,
                       orders: dict[str, sheets_flows.models.OrderReadSheets]):
    t = time.time()
    to_sync = []
    orders_db = await accounting_service.get_by_sheet_prefetched(cfg.spreadsheet, cfg.sheet_id)
    users = await auth_service.models.User.find_all().to_list()
    orders_db_map: dict[order_service.models.Order, list[accounting_service.models.UserOrder]] = {}

    for user_order in orders_db:
        order = cast(order_service.models.Order, user_order.order)
        if orders_db_map.get(order, None):
            orders_db_map[order].append(user_order)
        else:
            orders_db_map[order] = [user_order]

    for order, user_orders in orders_db_map.items():
        order_sheet = orders.get(order.order_id, None)
        if order_sheet is None:
            continue
        booster = accounting_service.boosters_to_str_sync(order, user_orders, users)
        if booster is not None and order_sheet.booster != booster:
            await order_service.update(order, order_service.models.OrderUpdate(booster=booster))
            to_sync.append((order.row_id, order_service.models.OrderUpdate(booster=booster)))

    if to_sync:
        (
            await sheets_flows.GoogleSheetsServiceManager
            .get()
            .update_rows_data(cfg.spreadsheet, cfg.sheet_id, to_sync)
        )
    logger.info(f"Syncing data to sheet[spreadsheet={cfg.spreadsheet} sheet_id={cfg.sheet_id}] "
                f"completed in {time.time() - t} | updated {len(to_sync)} orders")


@loop(minutes=5)
async def sync_data():
    cfgs = await sheets_service.get_all_not_default_booster()
    for cfg in cfgs:
        orders = (
            await sheets_flows.GoogleSheetsServiceManager
            .get()
            .get_all_data(sheets_flows.models.OrderReadSheets, cfg.spreadsheet, cfg.sheet_id))
        order_dict = {}
        for order in orders:
            order_dict[order.order_id] = order
        await sync_data_from(cfg, order_dict)
        order_dict = {}
        for order in orders:
            order_dict[order.order_id] = order
        await sync_data_to(cfg, order_dict)
