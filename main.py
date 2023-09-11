import os

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import ORJSONResponse
from starlette.staticfiles import StaticFiles
from beanie import init_beanie

from app import db, api
from app.core import config
from app.core.logging import logger
from app.core.extensions import configure_extensions
from app.middlewares.time import TimeMiddleware
from app.middlewares.exception import ExceptionMiddleware

from app.services.settings import service as settings_service
from app.services.auth import service as auth_service
from app.services.auth import flows as auth_flows
from app.services.telegram import service as telegram_service


if os.name != "nt":
    import uvloop  # noqa
    uvloop.install()

configure_extensions()


@asynccontextmanager
async def lifespan(application: FastAPI):  # noqa
    await init_beanie(connection_string=config.app.mongo_dsn, document_models=db.get_beanie_models())
    await settings_service.create()

    if not await auth_service.models.User.find_one({"name": config.app.super_user_username}):
        async with auth_flows.get_user_manager_context() as manager:
            user = auth_service.models.UserCreate(
                email=config.app.super_user_email,
                password=config.app.super_user_password,
                name=config.app.super_user_username,
                telegram="None",
                is_superuser=True,
                is_active=True,
                is_verified=True,
                discord='@system'
            )
            await manager.validate_password(user.password, user)
            user_dict = user.create_update_dict_superuser()
            password = user_dict.pop("password")
            user_dict["hashed_password"] = manager.password_helper.hash(password)
            await auth_service.models.User.model_validate(user_dict).create()
    await telegram_service.TelegramService.init()
    logger.info("Application... Online!")
    yield

app = FastAPI(openapi_url="")
app.add_middleware(ExceptionMiddleware)
app.add_middleware(TimeMiddleware)
app.mount("/static", StaticFiles(directory="static"), name="static")

api_app = FastAPI(
    title="DudeDuck CRM Backend",
    lifespan=lifespan,
    root_path="/api/v1",
    debug=False,
    default_response_class=ORJSONResponse,
)

api_app.include_router(api.router)

if config.app.cors_origins:
    from fastapi.middleware.cors import CORSMiddleware

    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.app.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "DELETE", "PATCH"],
        allow_headers=["*"],
    )

if config.app.use_correlation_id:
    from app.middlewares.correlation import CorrelationMiddleware

    app.add_middleware(CorrelationMiddleware)

app.mount("/api/v1", app=api_app)
