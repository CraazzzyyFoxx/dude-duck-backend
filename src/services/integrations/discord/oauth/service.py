import hikari
from cashews import cache
from fastapi import Depends
from fastapi.security import HTTPBearer
from hikari.urls import OAUTH2_API_URL
from passlib.hash import bcrypt
from starlette.requests import Request

from src.core import config, errors

oauth2_scheme = HTTPBearer()
discord_app = hikari.RESTApp()


async def get_tokens_from_response(code: str, state: str) -> hikari.OAuth2AuthorizationToken:
    async with discord_app.acquire() as client:
        token = await client.authorize_access_token(
            client=config.app.discord_client_id,
            client_secret=config.app.discord_client_secret,
            code=code,
            redirect_uri=f"{config.app.project_url}/discord/oauth/callback",
        )
        await cache.set(key=state, value=token, expire=3600)

    return token


async def logout(token: str):
    async with discord_app.acquire() as client:
        await client.revoke_access_token(config.app.discord_client_id, config.app.discord_client_secret, token)


async def is_authenticated(token: str):
    async with discord_app.acquire(token) as client:
        try:
            await client.fetch_authorization()
            return True
        except hikari.UnauthorizedError as e:
            raise errors.ApiHTTPException(
                status_code=401,
                detail=[errors.ApiException(msg="Could not validate credentials", code="unauthorized")],
            ) from e


async def refresh_access_token(refresh_token: str) -> hikari.OAuth2AuthorizationToken:
    async with discord_app.acquire() as client:
        return await client.refresh_access_token(
            config.app.discord_client_id,
            config.app.discord_client_secret,
            refresh_token,
        )


async def requires_authorization(token=Depends(oauth2_scheme)):
    return token.credentials


def get_oauth_url(request: Request):
    state = bcrypt.hash(f"{request.headers.raw}")
    scopes_raw = [
        hikari.OAuth2Scope.IDENTIFY,
        hikari.OAuth2Scope.GUILDS,
        hikari.OAuth2Scope.GUILDS_MEMBERS_READ,
        hikari.OAuth2Scope.GUILDS_JOIN,
    ]
    scopes = f"scope={'%20'.join(scopes_raw)}"
    client_id = f"client_id={config.app.discord_client_id}"
    redirect_uri = f"redirect_uri={config.app.project_url}/discord/oauth/callback"
    url = f"{OAUTH2_API_URL}/authorize?response_type=code&{client_id}&state={state}&{scopes}&{redirect_uri}"
    return {"url": url, "state": state}


async def fetch_user(token: str) -> hikari.OwnUser:
    async with discord_app.acquire(token) as client:
        return await client.fetch_my_user()
