import attrs
from cashews import Cache
from fastapi import APIRouter, Depends, Request
from fastapi.responses import ORJSONResponse
from starlette import status

from src import models
from src.core import config, enums, errors
from src.services.auth import flows as auth_flows

from . import service

router = APIRouter(
    prefix="/discord/oauth",
    tags=[enums.RouteTag.DISCORD_OAUTH],
)


cache = Cache()
cache.setup(config.app.redis_url.unicode_string())


@router.get("/get-url-login", status_code=status.HTTP_200_OK, name="Get Discord OAuth URL")
async def get_discord_oauth_url(request: Request):
    return ORJSONResponse(service.get_oauth_url(request))


@router.get("/get-url-connect", status_code=status.HTTP_200_OK, name="Get Discord OAuth URL")
async def get_discord_oauth_url(request: Request, user: models.User = Depends(auth_flows.current_active)):
    return ORJSONResponse(service.get_oauth_url(request))


@router.get("/callback", status_code=status.HTTP_200_OK)
async def callback(code: str, state: str = None):
    token = await service.get_tokens_from_response(code, state)
    return attrs.asdict(token)


@router.get("/finalize-login", status_code=status.HTTP_200_OK)
async def callback(state: str = None):
    token = await cache.get(state, None)
    if not token:
        raise errors.ApiHTTPException(
            status_code=status.HTTP_408_REQUEST_TIMEOUT,
            detail=[errors.ApiException(msg="Logged in for too long", code="token_expired")],
        ) from None
    user = await service.fetch_user(token.access_token)
    resp = ORJSONResponse(
        {
            "user": attrs.asdict(user),
            "accessToken": token.access_token,
            "refreshToken": token.refresh_token,
        }
    )
    return resp
