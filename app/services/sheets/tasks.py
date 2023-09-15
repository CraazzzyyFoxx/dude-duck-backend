import logging
import time

from beanie import PydanticObjectId, init_beanie
from deepdiff import DeepDiff

from app import db
from app.core import config
from app.services.accounting import models as accounting_models
from app.services.accounting import service as accounting_service
from app.services.auth import models as auth_models
from app.services.auth import service as auth_service
from app.services.currency import flows as currency_flows
from app.services.orders import models as order_models
from app.services.orders import service as order_service

from . import models, service


async def boosters_from_order_sync(
        order_id: PydanticObjectId,
        order: models.OrderReadSheets,
        users_in: list[auth_models.User]
) -> None:
    boosters_db = await accounting_service.get_by_order_id(order_id)
    if boosters_db:
        return

    completed = True if order.status == order_models.OrderStatus.Completed else False
    paid = True if order.status_paid == order_models.OrderPaidStatus.Paid else False
    boosters_db_map = {d.user_id: d for d in boosters_db}
    users_in_map = {user.name: user for user in users_in}
    boosters = accounting_service.boosters_from_str(order.booster)
    for booster, price in boosters.items():
        user: auth_models.User = users_in_map.get(booster)
        if user and not boosters_db_map.get(user.id):
            if price is None:
                price = order.price.price_booster_dollar
                dollars = await currency_flows.usd_to_currency(price, order.date, with_fee=True)
                dollars /= len(boosters)
            else:
                dollars = await currency_flows.currency_to_usd(price, order.date, currency="RUB")
            await accounting_service.create(accounting_models.UserOrderCreate(
                order_id=order_id,
                user_id=user.id,
                dollars=dollars,
                completed=completed,
                paid=paid
            ))


async def sync_data_from(
        cfg: models.OrderSheetParseRead,
        orders: dict[str, models.OrderReadSheets],
        users: list[auth_models.User],
        orders_db: dict[str, order_models.Order]
) -> None:
    t = time.time()
    deleted = 0
    changed = 0
    exclude = {'id', "revision_id", "booster"}

    for order_id, order_db in orders_db.items():
        order = orders.get(order_id)
        if order:
            orders.pop(order_id)
            if DeepDiff(order.model_dump(exclude=exclude), order_db.model_dump(exclude=exclude)):
                changed += 1
                await order_service.update(order_db, order_models.OrderUpdate.model_validate(order.model_dump()))
                await boosters_from_order_sync(order_db.id, order, users)
        else:
            deleted += 1
            await order_service.delete(order_db.id)
    insert_data = [
        order_models.OrderCreate.model_validate(order, from_attributes=True)
        for order in orders.values()
        if order.shop_order_id is not None
    ]
    created = len(insert_data)
    if created > 0:
        ids = await order_service.bulk_create(insert_data)
        for order_id, order in zip(ids, orders.values()):
            await boosters_from_order_sync(order_id, order, users)

    logging.info(f"Syncing data from sheet[spreadsheet={cfg.spreadsheet} sheet_id={cfg.sheet_id}] "
                 f"completed in {time.time() - t}. Created={created} Updated={changed} Deleted={deleted}")


async def sync_data_to(
        creds: auth_models.AdminGoogleToken,
        cfg: models.OrderSheetParseRead,
        orders: dict[str, models.OrderReadSheets],
        users: list[auth_models.User],
        orders_db: dict[PydanticObjectId, order_models.Order]
) -> None:
    t = time.time()
    to_sync = []
    user_orders_db = await accounting_service.get_by_orders([order.id for order in orders_db.values()])
    orders_db_map: dict[PydanticObjectId, list[accounting_service.models.UserOrder]] = {}

    for user_order in user_orders_db:
        order = orders_db.get(user_order.order_id)
        if orders_db_map.get(order.id, None):
            orders_db_map[order.id].append(user_order)
        else:
            orders_db_map[order.id] = [user_order]

    for order_id, user_orders in orders_db_map.items():
        order = orders_db.get(order_id)
        order_sheet = orders.get(order.order_id, None)
        if order_sheet is None:
            continue
        booster = await accounting_service.boosters_to_str_sync(order, user_orders, users)
        if booster is not None and order_sheet.booster != booster:
            to_sync.append((order.row_id, {"booster": booster}))

    if to_sync:
        service.update_rows_data(creds, cfg, to_sync)
    logging.info(f"Syncing data to sheet[spreadsheet={cfg.spreadsheet} sheet_id={cfg.sheet_id}] "
                 f"completed in {time.time() - t}. Updated {len(to_sync)} orders")


async def sync_orders() -> None:
    t = time.time()

    await init_beanie(connection_string=config.app.mongo_dsn, document_models=db.get_beanie_models())
    superuser = await auth_service.get_first_superuser()
    cfgs = await service.get_all_not_default_booster()
    for cfg in cfgs:
        cfg = models.OrderSheetParseRead.model_validate(cfg, from_attributes=True)
        orders_db = await order_service.get_all_by_sheet(cfg.spreadsheet, cfg.sheet_id)
        users = await auth_service.models.User.find_all().to_list()
        orders = service.get_all_data(superuser.google, models.OrderReadSheets, cfg)

        order_dict = {order.order_id: order for order in orders}
        order_db_dict = {order.order_id: order for order in orders_db}
        await sync_data_from(cfg, order_dict, users, order_db_dict)

        order_dict = {order.order_id: order for order in orders}
        order_db_dict = {order.id: order for order in orders_db}
        await sync_data_to(superuser.google, cfg, order_dict, users, order_db_dict)

    logging.info(f"Synchronization completed in {time.time() - t}")
