import time

import sqlalchemy as sa
from deepdiff import DeepDiff
from loguru import logger
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core import config, db, errors
from src.services.accounting import flows as accounting_flows
from src.services.accounting import models as accounting_models
from src.services.accounting import service as accounting_service
from src.services.auth import models as auth_models
from src.services.auth import service as auth_service
from src.services.currency import flows as currency_flows
from src.services.order import models as order_models
from src.services.order import service as order_service

from . import models, service


async def boosters_from_order_sync(
    session: AsyncSession,
    order_db: order_models.Order,
    order: models.OrderReadSheets,
    users_in: dict[str, auth_models.User],
    users_in_ids: dict[int, auth_models.User],
) -> None:
    boosters = await accounting_service.get_by_order_id(session, order_db.id)
    boosters_db_map: dict[int, accounting_models.UserOrder] = {d.user_id: d for d in boosters}
    str_boosters = await accounting_service.boosters_to_str_sync(session, order_db, boosters, users_in_ids.values())
    if order.booster is not None and str_boosters != order.booster:
        for booster, price in accounting_service.boosters_from_str(order.booster).items():
            user = users_in.get(booster)
            if user and boosters_db_map.get(user.id) is None:
                if price is None:
                    await accounting_flows.add_booster(session, order_db, user, sync=False)
                else:
                    try:
                        dollars = await currency_flows.currency_to_usd(session, price, order.date, currency="RUB")
                        await accounting_flows.add_booster_with_price(session, order_db, user, dollars, sync=False)
                    except errors.ApiHTTPException as e:
                        logger.error(e.detail)

    if order_db.status != order.status or order_db.status_paid != order.status_paid:
        update_model = accounting_models.UserOrderUpdate(
            completed=True if order.status == order_models.OrderStatus.Completed else False,
            paid=True if order.status_paid == order_models.OrderPaidStatus.Paid else False,
        )
        for b in boosters:
            await accounting_service.update(session, order_db, users_in_ids[b.user_id], update_model, sync=False)


async def sync_data_from(
    session: AsyncSession,
    cfg: models.OrderSheetParseRead,
    orders: dict[str, models.OrderReadSheets],
    users: dict[str, auth_models.User],
    users_ids: dict[int, auth_models.User],
    orders_db: dict[str, order_models.Order],
) -> None:
    t = time.time()
    created = 0
    deleted = 0
    changed = 0
    exclude = {"id", "booster", "created_at", "updated_at", "spreadsheet", "sheet_id", "row_id"}

    for order_id, order_db in orders_db.items():
        order = orders.get(order_id)
        if order is not None:
            orders.pop(order_id)
            por = models.OrderReadSheets.model_validate(order_db, from_attributes=True).model_dump(exclude=exclude)
            diff = DeepDiff(order.model_dump(exclude=exclude), por, truncate_datetime="second")
            if diff:
                if config.app.debug:
                    logger.debug(diff)
                try:
                    update_data = order_models.OrderUpdate.model_validate(order.model_dump())
                    order_db = await order_service.update(session, order_db, update_data)
                    changed += 1
                except ValidationError as e:
                    logger.error(e.errors(include_url=False))
            await boosters_from_order_sync(session, order_db, order, users, users_ids)
        # else:
        #     await order_service.delete(order_db.id)
        #     deleted += 1

    for order in orders.values():
        if order.shop_order_id is not None:
            try:
                insert_data = order_models.OrderCreate.model_validate(order.model_dump())
                order_db = await order_service.create(session, insert_data)
                await boosters_from_order_sync(session, order_db, order, users, users_ids)
                created += 1
            except ValidationError as e:
                logger.error(e.errors(include_url=False))

    logger.info(
        f"Syncing data from sheet[spreadsheet={cfg.spreadsheet} sheet_id={cfg.sheet_id}] "
        f"completed in {time.time() - t}. Created={created} Updated={changed} Deleted={deleted}"
    )


async def sync_data_to(
    session: AsyncSession,
    creds: auth_models.AdminGoogleTokenDB,
    cfg: models.OrderSheetParseRead,
    orders: dict[str, models.OrderReadSheets],
    users: list[auth_models.User],
    orders_db: dict[int, order_models.Order],
) -> None:
    t = time.time()
    to_sync = []
    user_orders_db = await accounting_service.get_by_orders(session, [order.id for order in orders_db.values()])
    orders_db_map: dict[int, list[accounting_models.UserOrder]] = {}

    for user_order in user_orders_db:
        order = orders_db[user_order.order_id]
        if orders_db_map.get(order.id, None):
            orders_db_map[order.id].append(user_order)
        else:
            orders_db_map[order.id] = [user_order]

    for order_id, user_orders in orders_db_map.items():
        order = orders_db[order_id]
        order_sheet = orders.get(order.order_id)
        if order_sheet is None:
            continue
        booster = await accounting_service.boosters_to_str_sync(session, order, user_orders, users)
        if booster is not None and order_sheet.booster != booster:
            to_sync.append((order.row_id, {"booster": booster}))
    if to_sync:
        service.update_rows_data(creds, cfg, to_sync)
    logger.info(
        f"Syncing data to sheet[spreadsheet={cfg.spreadsheet} sheet_id={cfg.sheet_id}] "
        f"completed in {time.time() - t}. Updated {len(to_sync)} orders"
    )


async def sync_orders() -> None:
    async with db.async_session_maker() as session:
        try:
            t = time.time()
            superuser = await auth_service.get_first_superuser(session)
            if superuser.google is None:
                logger.warning("Synchronization skipped, google token for first superuser missing")
                return
            query = sa.select(auth_models.User)
            users = await session.scalars(query)
            users_names_dict = {user.name: user for user in users}
            users_ids_dict = {user.id: user for user in users}
            for cfg in await service.get_all_not_default_user_read(session):
                orders: list[models.OrderReadSheets] = service.get_all_data(  # type: ignore
                    superuser.google, models.OrderReadSheets, cfg
                )
                orders_db = await order_service.get_all_by_sheet(session, cfg.spreadsheet, cfg.sheet_id)
                order_dict = {order.order_id: order for order in orders}
                order_db_dict = {order.order_id: order for order in orders_db}
                order_db_ids_dict = {order.id: order for order in orders_db}
                await sync_data_from(
                    session, cfg, order_dict.copy(), users_names_dict, users_ids_dict, order_db_dict.copy()
                )
                if config.app.sync_boosters:
                    await sync_data_to(
                        session, superuser.google, cfg, order_dict.copy(), users, order_db_ids_dict  # type: ignore
                    )
            logger.info(f"Synchronization completed in {time.time() - t}")
        except Exception as e:
            logger.exception(f"Error while sync_orders Error: {e}")
