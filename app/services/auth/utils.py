from fastapi import Depends
from fastapi.security import HTTPBearer
from fastapi.security.utils import get_authorization_scheme_param
from fastapi_users.authentication import AuthenticationBackend, BearerTransport
from fastapi_users.authentication.strategy import DatabaseStrategy
from fastapi_users_db_beanie.access_token import BeanieAccessTokenDatabase
from starlette.requests import Request

from app.services.auth import models


class DatabaseStrategyAPI(DatabaseStrategy):
    async def write_token(self, user: models.User) -> str:
        token = await models.AccessTokenAPI.find_one(models.AccessTokenAPI.user_id == user.id)
        if token:
            await token.delete()
        access_token_dict = self._create_access_token_dict(user)
        access_token = await self.database.create(access_token_dict)
        return access_token.token


class HTTPBearerAPI(HTTPBearer):
    async def __call__(
        self, request: Request
    ) -> str | None:
        authorization = request.headers.get("Authorization")
        scheme, credentials = get_authorization_scheme_param(authorization)
        if not (authorization and scheme and credentials):
            return None
        if scheme.lower() != "bearer":
            return None
        return credentials


class BearerTransportAPI(BearerTransport):
    scheme: HTTPBearerAPI

    def __init__(self, tokenUrl: str = "unknown"):
        super().__init__(tokenUrl)
        self.scheme = HTTPBearerAPI(bearerFormat="Bearer", auto_error=False)


bearer_transport = BearerTransport(tokenUrl="auth/login")
bearer_transport_api = BearerTransportAPI()


async def get_access_token_db():
    yield BeanieAccessTokenDatabase(models.AccessToken)


async def get_access_token_db_api():
    yield BeanieAccessTokenDatabase(models.AccessTokenAPI)


def get_database_strategy(
        access_token_db: BeanieAccessTokenDatabase = Depends(get_access_token_db),
) -> DatabaseStrategy:
    return DatabaseStrategy(access_token_db, lifetime_seconds=3600 * 24)


def get_database_strategy_api(
        access_token_db: BeanieAccessTokenDatabase = Depends(get_access_token_db_api),
) -> DatabaseStrategy:
    return DatabaseStrategyAPI(access_token_db)


auth_backend_api = AuthenticationBackend(
    name="api_db",
    transport=bearer_transport_api,
    get_strategy=get_database_strategy_api,
)

auth_backend_db = AuthenticationBackend(
    name="db",
    transport=bearer_transport,
    get_strategy=get_database_strategy,
)


async def get_enabled_backends(_: Request):
    return [auth_backend_db]


async def get_enabled_backends_api(_: Request):
    return [auth_backend_api]
