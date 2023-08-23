import enum

from pydantic import BaseModel, Field


class OrderMessage(BaseModel):
    order_id: str
    channel_id: int
    message_id: int


class OrderPull(BaseModel):
    config_names: list[str] = Field(min_items=1)


class OrderPullCreate(OrderPull):
    categories: list[str]


class OrderPullUpdate(OrderPull):
    pass


class MessageEnum(int, enum.Enum):
    SEND_ORDER = 0
    EDIT_ORDER = 1
    DELETE_ORDER = 2

    RESPONSE_ADMINS = 3
    RESPONSE_APPROVED = 4
    RESPONSE_DECLINED = 5

    REQUEST_VERIFY = 6
    VERIFIED = 7

    REQUEST_CLOSE_ORDER = 8

    LOGGED = 9
    REGISTERED = 10

    SENT_ORDER = 11
    EDITED_ORDER = 12
    DELETED_ORDER = 13

    RESPONSE_CHOSE = 14

    ORDER_PAID = 15


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
    created: list[SuccessPull] | None = Field(default=None)
    updated: list[SuccessPull] | None = Field(default=None)
    deleted: list[SuccessPull] | None = Field(default=None)
    skipped: list[SkippedPull] | None = Field(default=None)


class MessageResponse(BaseModel):
    status: MessageStatus
    channel_id: int


class MessageResponses(BaseModel):
    statuses: list[MessageResponse]
