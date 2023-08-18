from fastapi.security import HTTPBearer
from fastapi.security.utils import get_authorization_scheme_param
from fastapi_users.authentication import BearerTransport
from fastapi_users.authentication.strategy import DatabaseStrategy
from starlette.requests import Request

from app.services.auth import models


class DatabaseStrategyAPI(DatabaseStrategy):
    async def write_token(self, user: models.User) -> str:
        token = await models.AccessTokenAPI.find_one(models.AccessTokenAPI.user_id == user.id)
        await token.delete()
        access_token_dict = self._create_access_token_dict(user)
        access_token = await self.database.create(access_token_dict)
        return access_token.token


class HTTPBearerCustom(HTTPBearer):
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
    scheme: HTTPBearerCustom

    def __init__(self, tokenUrl: str = "unknown"):
        super().__init__(tokenUrl)
        self.scheme = HTTPBearerCustom(bearerFormat="Bearer", auto_error=False)
