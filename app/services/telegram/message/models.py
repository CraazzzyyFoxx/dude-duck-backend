import enum

from pydantic import BaseModel


class OrderMessage(BaseModel):
    order_id: int
    channel_id: int
    message_id: int


class OrderPull(BaseModel):
    config_names: list[str]
    preorder: bool = False
    is_gold: bool = False


class OrderPullCreate(OrderPull):
    categories: list[str]


class OrderPullUpdate(OrderPull):
    pass


class MessageStatus(str, enum.Enum):
    CREATED = "created"
    UPDATED = "updated"
    DELETED = "deleted"

    NOT_FOUND = "not_found"
    SAME_TEXT = "same_text"
    FORBIDDEN = "forbidden"
    EXISTS = "exists"


class SuccessPull(BaseModel):
    channel_id: int
    message_id: int
    status: MessageStatus


class SkippedPull(BaseModel):
    channel_id: int
    status: MessageStatus


class OrderResponse(BaseModel):
    created: list[SuccessPull]
    updated: list[SuccessPull]
    deleted: list[SuccessPull]
    skipped: list[SkippedPull]

    error: bool
    error_msg: str | None


class MessageResponse(BaseModel):
    status: MessageStatus
    channel_id: int


class MessageResponses(BaseModel):
    statuses: list[MessageResponse]
