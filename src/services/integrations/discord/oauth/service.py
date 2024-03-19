import hikari
import sqlalchemy as sa
from cashews import Cache
from hikari.urls import OAUTH2_API_URL
from passlib.hash import bcrypt
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from src.core import config
from src import models, schemas
from src.schemas import DiscordOAuthUrl
from src.utils import jwt

cache = Cache()
cache.setup(config.app.redis_url.unicode_string())
discord_app = hikari.RESTApp()


async def get_by_user_id(session: AsyncSession, user_id: int) -> models.OAuthUser | None:
    query = sa.select(models.OAuthUser).where(
        models.OAuthUser.user_id == user_id, models.OAuthUser.oauth_name == "discord"
    )
    result = await session.execute(query)
    return result.scalars().first()


async def create(
    session: AsyncSession,
    user_id: int,
    token: hikari.OAuth2AuthorizationToken,
    discord_user: hikari.OwnUser,
) -> models.OAuthUser:
    user = models.OAuthUser(
        user_id=user_id,
        oauth_name="discord",
        access_token=token.access_token,
        expires_at=int(token.expires_in.total_seconds()),
        refresh_token=token.refresh_token,
        account_id=str(discord_user.id),
        account_email=discord_user.email,
    )
    session.add(user)
    await session.commit()
    return user


async def update(
    session: AsyncSession,
    oauth_user: models.OAuthUser,
    token: hikari.OAuth2AuthorizationToken,
    discord_user: hikari.OwnUser,
) -> models.OAuthUser:
    oauth_user.access_token = token.access_token
    oauth_user.expires_at = int(token.expires_in.total_seconds())
    oauth_user.refresh_token = token.refresh_token
    oauth_user.account_id = str(discord_user.id)
    oauth_user.account_email = discord_user.email
    await session.commit()
    return oauth_user


async def get_tokens_from_response(code: str, state: str) -> hikari.OAuth2AuthorizationToken:
    async with discord_app.acquire() as client:
        token = await client.authorize_access_token(
            client=config.app.discord_client_id,
            client_secret=config.app.discord_client_secret,
            code=code,
            redirect_uri=f"{config.app.project_url}/discord/oauth/callback",
        )
        await cache.set(key=state, value=token, expire=900)

    return token


async def refresh_access_token(refresh_token: str) -> hikari.OAuth2AuthorizationToken:
    async with discord_app.acquire() as client:
        return await client.refresh_access_token(
            config.app.discord_client_id,
            config.app.discord_client_secret,
            refresh_token,
        )


def get_oauth_url(request: Request, user: schemas.UserRead) -> DiscordOAuthUrl:
    state = bcrypt.hash(f"{request.headers.raw}")
    state_jwt = jwt.generate_jwt(
        {"state": state, "user": user.model_dump(mode="json"), "aud": config.app.discord_oauth_token_audience},
        config.app.discord_oauth_secret,
        900,
    )
    scopes_raw = [
        hikari.OAuth2Scope.EMAIL,
        hikari.OAuth2Scope.IDENTIFY,
        hikari.OAuth2Scope.GUILDS,
        hikari.OAuth2Scope.GUILDS_MEMBERS_READ,
        hikari.OAuth2Scope.GUILDS_JOIN,
    ]
    scopes = f"scope={'%20'.join(scopes_raw)}"
    client_id = f"client_id={config.app.discord_client_id}"
    redirect_uri = f"redirect_uri={config.app.project_url}/discord/oauth/callback"
    url = f"{OAUTH2_API_URL}/authorize?response_type=code&{client_id}&state={state_jwt}&{scopes}&{redirect_uri}"
    return DiscordOAuthUrl(url=url, state=state)


async def fetch_user(token: str) -> hikari.OwnUser:
    async with discord_app.acquire(token) as client:
        return await client.fetch_my_user()
