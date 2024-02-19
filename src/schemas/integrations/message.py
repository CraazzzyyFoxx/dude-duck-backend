
import typing
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Select

from src.core import enums, pagination

__all__ = (
    "MessageRead",
    "OrderMessageRead",
    "ResponseMessageRead",
    "UserMessageRead",
    "CreateMessage",
    "CreateOrderMessage",
    "CreateResponseMessage",
    "CreateUserMessage",
    "UpdateMessage",
    "UpdateOrderMessage",
    "UpdateResponseMessage",
    "UpdateUserMessage",
    "DeleteMessage",
    "DeleteOrderMessage",
    "DeleteResponseMessage",
    "DeleteUserMessage",
    "SuccessCallback",
    "SkippedCallback",
    "MessageCallback",
    "OrderMessagePaginationParams",
    "ResponseMessagePaginationParams",
    "UserMessagePaginationParams",
)

from src.models import CallbackStatus


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    channel_id: int
    message_id: int
    integration: enums.Integration
    is_deleted: bool
    created_at: datetime


class OrderMessageRead(MessageRead):
    order_id: int
    is_preorder: bool


class ResponseMessageRead(MessageRead):
    order_id: int
    user_id: int
    is_preorder: bool


class UserMessageRead(MessageRead):
    user_id: int


class CreateMessage(BaseModel):
    integration: enums.Integration


class CreateOrderMessage(CreateMessage):
    order_id: int
    is_preorder: bool = False
    categories: list[str]
    configs: list[str] = Field(default=[])
    is_gold: bool = False


class CreateResponseMessage(CreateMessage):
    order_id: int
    user_id: int
    is_preorder: bool = False
    is_gold: bool = False


class CreateUserMessage(CreateMessage):
    user_id: int | typing.Literal["@everyone"]
    text: str


class UpdateMessage(BaseModel):
    integration: enums.Integration
    text: str | None = None


class UpdateOrderMessage(UpdateMessage):
    order_id: int
    is_preorder: bool = False
    configs: list[str] = Field(default=[])
    is_gold: bool = False


class UpdateResponseMessage(UpdateMessage):
    order_id: int
    user_id: int
    is_preorder: bool = False
    is_gold: bool = False


class UpdateUserMessage(UpdateMessage):
    user_id: int
    message_id: int


class DeleteMessage(BaseModel):
    integration: enums.Integration


class DeleteOrderMessage(DeleteMessage):
    order_id: int
    is_preorder: bool = False


class DeleteResponseMessage(DeleteMessage):
    order_id: int
    user_id: int
    is_preorder: bool = False


class DeleteUserMessage(DeleteMessage):
    user_id: int
    message_id: int


class SuccessCallback(BaseModel):
    channel_id: int
    message_id: int
    status: CallbackStatus


class SkippedCallback(BaseModel):
    channel_id: int
    status: CallbackStatus


class MessageCallback(BaseModel):
    created: list[SuccessCallback] = Field(default=[])
    updated: list[SuccessCallback] = Field(default=[])
    deleted: list[SuccessCallback] = Field(default=[])
    skipped: list[SkippedCallback] = Field(default=[])

    error: bool = Field(default=False)
    error_msg: str | None = Field(default=None)


class OrderMessagePaginationParams(pagination.PaginationParams):
    integration: enums.Integration
    channel_id: int | None = None
    order_id: int | None = None
    is_preorder: bool | None = None

    def apply_filter(self, query: Select) -> Select:
        query = query.where(OrderMessage.integration == self.integration)
        if self.channel_id:
            query = query.where(OrderMessage.channel_id == self.channel_id)
        if self.order_id:
            query = query.where(OrderMessage.order_id == self.order_id)
        if self.is_preorder is not None:
            query = query.where(OrderMessage.is_preorder == self.is_preorder)
        return query


class ResponseMessagePaginationParams(pagination.PaginationParams):
    integration: enums.Integration
    order_id: int | None = None
    user_id: int | None = None

    def apply_filter(self, query: Select) -> Select:
        query = query.where(ResponseMessage.integration == self.integration)
        if self.order_id:
            query = query.where(ResponseMessage.order_id == self.order_id)
        if self.user_id:
            query = query.where(ResponseMessage.user_id == self.user_id)
        return query


class UserMessagePaginationParams(pagination.PaginationParams):
    integration: enums.Integration
    user_id: int | None = None

    def apply_filter(self, query: Select) -> Select:
        query = query.where(UserMessage.integration == self.integration)
        if self.user_id:
            query = query.where(UserMessage.user_id == self.user_id)
        return query
