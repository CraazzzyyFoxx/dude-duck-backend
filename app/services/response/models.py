from datetime import datetime, timedelta

from beanie import Document, PydanticObjectId
from pydantic import BaseModel, ConfigDict, Field
from pymongo import IndexModel

__all__ = (
    "ResponseExtra",
    "Response",
    "ResponseUpdate",
    "ResponseCreate",
    "ResponseRead"
)


class ResponseExtra(BaseModel):
    text: str | None = None
    price: float | None = None
    start_date: datetime | None = None
    eta: timedelta | None = None


class Response(Document):
    order_id: PydanticObjectId
    user_id: PydanticObjectId

    refund: bool = Field(default=False)
    approved: bool = Field(default=False)
    closed: bool = Field(default=False)
    extra: ResponseExtra

    created_at: datetime = Field(default_factory=datetime.utcnow)
    approved_at: datetime | None = None

    class Settings:
        indexes = [
            IndexModel(["order_id", "user_id"], unique=True),
        ]
        use_state_management = True
        state_management_save_previous = True


class ResponseCreate(BaseModel):
    order_id: PydanticObjectId
    user_id: PydanticObjectId
    extra: ResponseExtra


class ResponseRead(BaseModel):
    order_id: PydanticObjectId
    user_id: PydanticObjectId

    refund: bool
    approved: bool
    closed: bool
    extra: ResponseExtra


class ResponseUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    refund: bool | None = None
    approved: bool
    closed: bool
