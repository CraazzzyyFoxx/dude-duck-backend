from pydantic import BaseModel


__all__ = ("OAuthUserRead", )


class OAuthUserRead(BaseModel):
    oauth_name: str
    access_token: str
    expires_at: int | None
    refresh_token: str | None
    account_id: str
    account_email: str