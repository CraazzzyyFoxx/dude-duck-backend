from datetime import datetime

from pydantic import BaseModel, ConfigDict


__all__ = ("TelegramAccountCreate", "TelegramAccountRead")


class TelegramAccountCreate(BaseModel):
    account_id: int
    username: str
    first_name: str


class TelegramAccountRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    account_id: int
    username: str
    first_name: str
    created_at: datetime
