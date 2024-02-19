from pydantic import BaseModel


class DiscordOAuthUrl(BaseModel):
    url: str
    state: str
