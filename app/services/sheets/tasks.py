import time
from typing import cast

from beanie import init_beanie
from loguru import logger
from deepdiff import DeepDiff

from app import db
from app.core import config
from app.services.auth import models as auth_models
from app.services.auth import flows as auth_flows
from app.services.auth import service as auth_service
from app.services.orders import service as order_service
from app.services.orders import models as order_models
from app.services.accounting import service as accounting_service

from . import models, service


async def sync_data_from(
        cfg: models.OrderSheetParseRead,
        orders: dict[str, models.OrderReadSheets],
        users: list[auth_models.User],
        orders_db: list[order_models.Order]
):
    t = time.time()
    for order in orders_db:
        s_order = orders.get(order.order_id, None)
        if s_order is None:
            await order_service.delete(order.id)
        else:
            orders.pop(s_order.order_id)
            changes = DeepDiff(order.model_dump(exclude={'id', "revision_id"}),
                               s_order.model_dump(exclude={'id', "revision_id"}))
            if changes:
                s_order.booster = None
                await order_service.update(order, s_order)  # type: ignore
            await accounting_service.boosters_from_order_sync(order, users)
    for order_s in orders.values():
        if order_s.shop_order_id is not None:
            order = await order_service.create(order_s)  # type: ignore
            await accounting_service.boosters_from_order_sync(order, users)

    logger.info(f"Syncing data from sheet[spreadsheet={cfg.spreadsheet} sheet_id={cfg.sheet_id}] "
                f"completed in {time.time() - t}")


async def sync_data_to(
        creds: auth_models.AdminGoogleToken,
        cfg: models.OrderSheetParseRead,
        orders: dict[str, models.OrderReadSheets],
        users: list[auth_models.User],
):
    t = time.time()
    to_sync = []
    orders_db = await accounting_service.get_by_sheet_prefetched(cfg.spreadsheet, cfg.sheet_id)
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
        booster = await accounting_service.boosters_to_str_sync(order, user_orders, users)
        if booster is not None and order_sheet.booster != booster:
            to_sync.append((order.row_id, {"booster": booster}))

    if to_sync:
        service.update_rows_data(creds, cfg, to_sync)
    logger.info(f"Syncing data to sheet[spreadsheet={cfg.spreadsheet} sheet_id={cfg.sheet_id}] "
                f"completed in {time.time() - t} | updated {len(to_sync)} orders")


async def sync_orders():
    await init_beanie(connection_string=config.app.mongo_dsn, document_models=db.get_beanie_models())
    super_user = await auth_flows.get_booster_by_name(config.app.super_user_username)
    cfgs = await service.get_all_not_default_booster()
    for cfg in cfgs:
        cfg = models.OrderSheetParseRead.model_validate(cfg)
        orders_db = await order_service.get_all_by_sheet(cfg.spreadsheet, cfg.sheet_id)
        users = await auth_service.models.User.find_all().to_list()
        orders = service.get_all_data(super_user.google, models.OrderReadSheets, cfg)
        order_dict = {}
        for order in orders:
            order_dict[order.order_id] = order
        await sync_data_from(cfg, order_dict, users, orders_db)
        order_dict = {}
        for order in orders:
            order_dict[order.order_id] = order
        await sync_data_to(super_user.google, cfg, order_dict, users)
