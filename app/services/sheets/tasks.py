import logging
import time

from beanie import PydanticObjectId, init_beanie
from deepdiff import DeepDiff
from pydantic import ValidationError

from app import db
from app.core import config
from app.services.accounting import flows as accounting_flows
from app.services.accounting import service as accounting_service
from app.services.auth import models as auth_models
from app.services.auth import service as auth_service
from app.services.currency import flows as currency_flows
from app.services.orders import models as order_models
from app.services.orders import service as order_service

from . import models, service


async def boosters_from_order_sync(
    order_db: order_models.Order, order: models.OrderReadSheets, users_in: list[auth_models.User]
) -> None:
    boosters = await accounting_service.get_by_order_id(order_db.id)
    if await accounting_service.boosters_to_str_sync(order, boosters, users_in) != order.booster:
        boosters_db_map: dict[PydanticObjectId, auth_models.User] = {d.user_id: d for d in boosters}
        users_in_map: dict[str, auth_models.User] = {user.name: user for user in users_in}
        for booster, price in accounting_service.boosters_from_str(order.booster).items():
            user = users_in_map.get(booster)
            if user and boosters_db_map.get(user.id) is None:
                if price is None:
                    await accounting_flows.add_booster(order_db, user)
                else:
                    dollars = await currency_flows.currency_to_usd(price, order.date, currency="RUB")
                    await accounting_flows.add_booster_with_price(order_db, user, dollars)


async def sync_data_from(
    cfg: models.OrderSheetParseRead,
    orders: dict[str, models.OrderReadSheets],
    users: list[auth_models.User],
    orders_db: dict[str, order_models.Order],
) -> None:
    t = time.time()
    deleted = 0
    changed = 0
    exclude = {"id", "revision_id", "booster", "created_at", "updated_at"}

    for order_id, order_db in orders_db.items():
        order = orders.get(order_id)
        if order is not None and order.status != order_models.OrderStatus.Refund:
            orders.pop(order_id)
            if DeepDiff(order.model_dump(exclude=exclude), order_db.model_dump(exclude=exclude)):
                await order_service.update(order_db, order_models.OrderUpdate.model_validate(order.model_dump()))
                changed += 1
            await boosters_from_order_sync(order_db, order, users)
        else:
            orders.pop(order_id)
            await order_service.delete(order_db.id)
            deleted += 1

    insert_data = []
    inserted_orders = []
    for order in orders.values():
        if (
            order.shop_order_id is not None
            and order.status != order_models.OrderStatus.Refund
            and order.price.price_booster_dollar is not None
        ):
            try:
                insert_data.append(order_models.OrderCreate.model_validate(order, from_attributes=True))
                inserted_orders.append(order)
            except ValidationError:
                pass
    created = len(insert_data)
    if created > 0:
        ids = await order_service.bulk_create(insert_data)
        orders_db = {o.order_id: o for o in await order_service.get_by_ids(ids)}
        for order in inserted_orders:
            await boosters_from_order_sync(orders_db[order.order_id], order, users)

    logging.info(
        f"Syncing data from sheet[spreadsheet={cfg.spreadsheet} sheet_id={cfg.sheet_id}] "
        f"completed in {time.time() - t}. Created={created} Updated={changed} Deleted={deleted}"
    )


async def sync_data_to(
    creds: auth_models.AdminGoogleToken,
    cfg: models.OrderSheetParseRead,
    orders: dict[str, models.OrderReadSheets],
    users: list[auth_models.User],
    orders_db: dict[PydanticObjectId, order_models.Order],
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
        order_sheet = orders.get(order.order_id)
        if order_sheet is None:
            continue
        booster = await accounting_service.boosters_to_str_sync(order, user_orders, users)
        if booster is not None and order_sheet.booster != booster:
            to_sync.append((order.row_id, {"booster": booster}))
    if to_sync:
        service.update_rows_data(creds, cfg, to_sync)
    logging.info(
        f"Syncing data to sheet[spreadsheet={cfg.spreadsheet} sheet_id={cfg.sheet_id}] "
        f"completed in {time.time() - t}. Updated {len(to_sync)} orders"
    )


async def sync_orders() -> None:
    t = time.time()
    await init_beanie(connection_string=config.app.mongo_dsn, document_models=db.get_beanie_models())
    superuser = await auth_service.get_first_superuser()
    if superuser.google is None:
        logging.warning("Synchronization skipped, google token for first superuser missing")
        return
    users = await auth_service.get_all()
    for cfg in await service.get_all_not_default_user_read():
        orders = service.get_all_data(superuser.google, models.OrderReadSheets, cfg)
        orders_db = await order_service.get_all_by_sheet(cfg.spreadsheet, cfg.sheet_id)
        order_dict = {order.order_id: order for order in orders}
        order_db_dict = {order.order_id: order for order in orders_db}
        await sync_data_from(cfg, order_dict.copy(), users, order_db_dict.copy())
        if config.app.sync_boosters:
            await sync_data_to(superuser.google, cfg, order_dict.copy(), users, order_db_dict.copy())
    logging.info(f"Synchronization completed in {time.time() - t}")
