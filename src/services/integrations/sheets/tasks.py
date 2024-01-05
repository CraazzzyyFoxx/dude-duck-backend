import time
import typing

import sqlalchemy as sa
from deepdiff import DeepDiff
from loguru import logger
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from src import models
from src.core import config, db, errors
from src.services.accounting import flows as accounting_flows
from src.services.accounting import service as accounting_service
from src.services.auth import service as auth_service
from src.services.currency import flows as currency_flows
from src.services.order import service as order_service
from src.services.screenshot import service as screenshot_service

from . import service


async def boosters_from_order_sync(
    session: AsyncSession,
    order_db: models.Order,
    order: models.OrderReadSheets,
    users_in: dict[str, models.User],
    users_in_ids: dict[int, models.User],
) -> None:
    boosters = await accounting_service.get_by_order_id(session, order_db.id)
    boosters_db_map: dict[int, models.UserOrder] = {d.user_id: d for d in boosters}
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
                        logger.error(
                            f"Error while add booster {user.name} [id: {user.id}] "
                            f"to order {order.order_id} [id: {order.id}] Error: {e}"
                        )

    for b in boosters:
        if b.completed != (order.status == models.OrderStatus.Completed) or b.paid != (
            order.status_paid == models.OrderPaidStatus.Paid
        ):
            update_model = models.UserOrderUpdate(
                completed=True if order.status == models.OrderStatus.Completed else False,
                paid=True if order.status_paid == models.OrderPaidStatus.Paid else False,
            )
            await accounting_service.update(
                session, order_db, users_in_ids[b.user_id], update_model, sync=False, patch=True
            )


async def sync_data_from(
    session: AsyncSession,
    user: models.User,
    cfg: models.OrderSheetParseRead,
    orders: dict[str, models.OrderReadSheets],
    users: dict[str, models.User],
    users_ids: dict[int, models.User],
    orders_db: dict[str, models.Order],
) -> None:
    t = time.time()
    created = 0
    deleted = 0
    changed = 0
    exclude = {
        "id",
        "booster",
        "created_at",
        "updated_at",
        "spreadsheet",
        "sheet_id",
        "row_id",
        "screenshot",
    }

    for order_id, order_db in orders_db.items():
        order = orders.get(order_id)
        if order is not None:
            orders.pop(order_id)
            por = models.OrderReadSheets.model_validate(order_db, from_attributes=True).model_dump(exclude=exclude)
            diff = DeepDiff(por, order.model_dump(exclude=exclude), truncate_datetime="second")
            if diff:
                if config.app.debug:
                    logger.info(diff)
                try:
                    update_data = models.OrderUpdate.model_validate(order.model_dump())
                    if update_data.status == models.OrderStatus.Refund:
                        await order_service.delete(session, order_db.id)
                        deleted += 1
                        continue
                    order_db = await order_service.update(session, order_db, update_data)
                    changed += 1
                except ValidationError as e:
                    logger.error(e.errors(include_url=False))
            await boosters_from_order_sync(session, order_db, order, users, users_ids)
            if order.screenshot is not None:
                urls = screenshot_service.find_url_in_text(order.screenshot)
                urls_db = [screenshot.url for screenshot in order_db.screenshots]
                await screenshot_service.bulk_create(
                    session, user, order_db, [url for url in urls if url not in urls_db]
                )
        # else:
        #     await order_service.delete(order_db.id)
        #     deleted += 1

    for order in orders.values():
        if order.shop_order_id is not None:
            try:
                insert_data = models.OrderCreate.model_validate(order.model_dump())
                order_db = await order_service.create(session, insert_data)
                await boosters_from_order_sync(session, order_db, order, users, users_ids)
                if order.screenshot is not None:
                    urls = screenshot_service.find_url_in_text(order.screenshot)
                    await screenshot_service.bulk_create(session, user, order_db, urls)
                created += 1
            except ValidationError:
                logger.error(f"Skipping order {order.order_id} validation error")

    logger.info(
        f"Syncing data from sheet[spreadsheet={cfg.spreadsheet} sheet_id={cfg.sheet_id}] "
        f"completed in {time.time() - t}. Created={created} Updated={changed} Deleted={deleted}"
    )


async def sync_data_to(
    session: AsyncSession,
    token: models.AdminGoogleTokenDB,
    cfg: models.OrderSheetParseRead,
    orders: dict[str, models.OrderReadSheets],
    users: typing.Iterable[models.User],
    orders_db: dict[int, models.Order],
) -> None:
    t = time.time()
    to_sync = []
    user_orders_db = await accounting_service.get_by_orders(session, [order.id for order in orders_db.values()])
    orders_db_map: dict[int, list[models.UserOrder]] = {}

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
        service.update_rows_data(token, cfg, to_sync)
    logger.info(
        f"Syncing data to sheet[spreadsheet={cfg.spreadsheet} sheet_id={cfg.sheet_id}] "
        f"completed in {time.time() - t}. Updated {len(to_sync)} orders"
    )


async def sync_orders() -> None:
    async with db.async_session_maker() as session:
        try:
            t = time.time()
            token = await service.get_first_superuser_token(session)
            super_user = await auth_service.get_first_superuser(session)
            if not token:
                logger.warning("Synchronization skipped, google token for first superuser missing")
                return
            users = list(await session.scalars(sa.select(models.User)))
            users_names_dict = {user.name: user for user in users}
            users_ids_dict = {user.id: user for user in users}
            for cfg in await service.get_all_not_default_user_read(session):
                t1 = time.time()
                orders: list[models.OrderReadSheets] = service.get_all_data(  # type: ignore
                    token.token, models.OrderReadSheets, cfg
                )
                logger.info(
                    f"Getting data from sheet[spreadsheet={cfg.spreadsheet} "
                    f"sheet_id={cfg.sheet_id}] completed in {time.time() - t1}, collected {len(orders)} orders"
                )
                orders_db = await order_service.get_all_by_sheet(session, cfg.spreadsheet, cfg.sheet_id)
                order_dict = {order.order_id: order for order in orders}
                order_db_dict = {order.order_id: order for order in orders_db}
                order_db_ids_dict = {order.id: order for order in orders_db}
                await sync_data_from(
                    session,
                    super_user,
                    cfg,
                    order_dict.copy(),
                    users_names_dict,
                    users_ids_dict.copy(),
                    order_db_dict.copy(),
                )
                if config.app.sync_boosters:
                    await sync_data_to(
                        session,
                        token.token,
                        cfg,
                        order_dict.copy(),
                        users,
                        order_db_ids_dict,
                    )
            logger.info(f"Synchronization completed in {time.time() - t}")
        except Exception as e:
            logger.exception(f"Error while sync_orders Error: {e}")
