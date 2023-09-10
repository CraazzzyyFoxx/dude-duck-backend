import enum

from pydantic import BaseModel


class OrderMessage(BaseModel):
    order_id: str
    channel_id: int
    message_id: int


class OrderPull(BaseModel):
    config_names: list[str]
    preorder: bool = False


class OrderPullCreate(OrderPull):
    categories: list[str]


class OrderPullUpdate(OrderPull):
    pass


class MessageEnum(int, enum.Enum):
    SEND_ORDER = 0
    EDIT_ORDER = 1
    DELETE_ORDER = 2

    RESPONSE_ORDER_ADMINS = 3
    RESPONSE_ORDER_APPROVED = 4
    RESPONSE_ORDER_DECLINED = 5

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

    SEND_PREORDER = 16
    EDIT_PREORDER = 17
    DELETE_PREORDER = 18

    SENT_PREORDER = 19
    EDITED_PREORDER = 20
    DELETED_PREORDER = 21

    RESPONSE_PREORDER_ADMINS = 22
    RESPONSE_PREORDER_APPROVED = 23
    RESPONSE_PREORDER_DECLINED = 24


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
