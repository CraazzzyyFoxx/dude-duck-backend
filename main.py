import os
from contextlib import asynccontextmanager

from cashews import cache
from fastapi import FastAPI
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import ORJSONResponse
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware
from starlette.requests import Request
from starlette.staticfiles import StaticFiles

from src import api
from src.core import config, db
from src.core.extensions import configure_extensions
from src.core.logging import logger
from src.middlewares.exception import ExceptionMiddleware
from src.middlewares.time import TimeMiddleware
from src.services.auth import flows as auth_flows
from src.services.integrations.discord import service as discord_service
from src.services.integrations.discord.oauth.service import discord_app
from src.services.integrations.telegram import service as telegram_service
from src.services.settings import service as settings_service

if os.name != "nt":
    import uvloop  # noqa

    uvloop.install()

configure_extensions()
cache.setup("mem://")


@asynccontextmanager
async def lifespan(_: FastAPI):
    db.Base.metadata.create_all(db.engine)
    async with db.async_session_maker() as session:
        await settings_service.create(session)
        await auth_flows.create_first_superuser(session)
    await discord_app.start()
    logger.info("Application... Online!")
    yield
    await telegram_service.telegram_client.aclose()
    await discord_service.discord_client.aclose()
    await discord_app.close()


async def not_found(request: Request, _: Exception):
    return ORJSONResponse(status_code=404, content={"detail": [{"msg": "Not Found"}]})


exception_handlers = {404: not_found}


app = FastAPI(
    docs_url="/api/v1/docs",
    redoc_url="/api/v1/redoc",
    lifespan=lifespan,
    default_response_class=ORJSONResponse,
    debug=config.app.debug,
    exception_handlers=exception_handlers,
)
app.add_middleware(ExceptionMiddleware)
app.add_middleware(SentryAsgiMiddleware)
app.add_middleware(TimeMiddleware)
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(api.router)
