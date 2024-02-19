from fastapi import APIRouter, Depends, Request
from fastapi.responses import ORJSONResponse
from starlette import status

from src import models, schemas
from src.core import enums, db, config
from src.services.auth import flows as auth_flows
from src.utils import jwt

from . import service

router = APIRouter(
    prefix="/discord/oauth",
    tags=[enums.RouteTag.DISCORD_OAUTH],
)


# @router.get("/get-url-login", status_code=status.HTTP_200_OK, response_model=schemas.DiscordOAuthUrl)
# async def get_discord_oauth_url(request: Request):
#     return service.get_oauth_url(request)


@router.get("/get-url-connect", status_code=status.HTTP_200_OK, response_model=schemas.DiscordOAuthUrl)
async def get_discord_oauth_url(request: Request, user: models.User = Depends(auth_flows.current_active)):
    return service.get_oauth_url(request, models.UserRead.model_validate(user, from_attributes=True))


@router.get("/callback", status_code=status.HTTP_200_OK)
async def callback(code: str, state: str, session=Depends(db.get_async_session)):
    token = await service.get_tokens_from_response(code, state)
    user = jwt.decode_jwt(state, config.app.discord_oauth_secret, config.app.discord_oauth_token_audience)["user"]
    user_discord = await service.fetch_user(token.access_token)
    oauth_user = await service.get_by_user_id(session, user["id"])
    if oauth_user is None:
        await service.create(session, user["id"], token, user_discord)
    else:
        await service.update(session, oauth_user, token, user_discord)
    return ORJSONResponse({"status": "ok"})
