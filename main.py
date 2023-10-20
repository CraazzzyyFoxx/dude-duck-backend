import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import ORJSONResponse
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware
from starlette.staticfiles import StaticFiles

from app import api
from app.core import config, db
from app.core.extensions import configure_extensions
from app.core.logging import logger
from app.middlewares.exception import ExceptionMiddleware
from app.middlewares.time import TimeMiddleware
from app.services.auth import flows as auth_flows
from app.services.telegram import service as telegram_service

if os.name != "nt":
    import uvloop  # noqa

    uvloop.install()

configure_extensions()


@asynccontextmanager
async def lifespan(_: FastAPI):
    # await Tortoise.init(config=config.tortoise)
    # await settings_service.create()
    async with db.async_session_maker() as session:
        await auth_flows.create_first_superuser(session)
    await telegram_service.TelegramService.init()
    logger.info("Application... Online!")
    yield
    await telegram_service.TelegramService.shutdown()
    # await connections.close_all()


async def not_found(request, exc):
    return ORJSONResponse(status_code=404, content={"detail": [{"msg": "Not Found"}]})


exception_handlers = {404: not_found}


app = FastAPI(
    openapi_url="",
    lifespan=lifespan,
    default_response_class=ORJSONResponse,
    debug=config.app.debug,
    exception_handlers=exception_handlers,
)
app.add_middleware(ExceptionMiddleware)
app.add_middleware(SentryAsgiMiddleware)
app.add_middleware(TimeMiddleware)
app.mount("/static", StaticFiles(directory="static"), name="static")

api_app = FastAPI(
    title="DudeDuck CRM Backend",
    root_path="/api/v1",
    debug=config.app.debug,
    default_response_class=ORJSONResponse,
)
api_app.add_middleware(ExceptionMiddleware)
api_app.include_router(api.router)

if config.app.cors_origins:
    from fastapi.middleware.cors import CORSMiddleware

    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.app.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "DELETE", "PATCH", "PUT"],
        allow_headers=["*"],
    )

if config.app.use_correlation_id:
    from app.middlewares.correlation import CorrelationMiddleware

    app.add_middleware(CorrelationMiddleware)

app.mount("/api/v1", app=api_app)
