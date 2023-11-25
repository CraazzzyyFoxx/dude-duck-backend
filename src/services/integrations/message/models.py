import enum
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import BigInteger, Enum, Select, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.core import db, enums, pagination


class OrderPull(BaseModel):
    integration: enums.Integration
    preorder: bool = False


class OrderPullCreate(OrderPull):
    categories: list[str]
    config_names: list[str] = Field(default=[])
    is_gold: bool = False


class OrderPullUpdate(OrderPull):
    config_names: list[str] = Field(default=[])
    is_gold: bool = False


class OrderPullDelete(OrderPull):
    pass


class MessageType(str, enum.Enum):
    ORDER = "order"
    PRE_ORDER = "pre_order"
    RESPONSE = "response"
    MESSAGE = "message"


class MessageStatus(str, enum.Enum):
    CREATED = "created"
    UPDATED = "updated"
    DELETED = "deleted"

    NOT_FOUND = "not_found"
    SAME_TEXT = "same_text"
    FORBIDDEN = "forbidden"
    EXISTS = "exists"

    INTEGRATION_NOT_FOUND = "integration not found"


class Message(db.TimeStampMixin):
    __tablename__ = "integration_message"
    __table_args__ = (UniqueConstraint("channel_id", "message_id", name="idx_channel_message"),)

    order_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    channel_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    message_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    type: Mapped[MessageType] = mapped_column(Enum(MessageType))
    integration: Mapped[enums.Integration] = mapped_column(Enum(enums.Integration))


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    order_id: int | None = None
    user_id: int | None = None
    channel_id: int
    message_id: int

    integration: enums.Integration
    type: MessageType

    is_deleted: bool
    created_at: datetime


class MessageCreate(BaseModel):
    order_id: int | None = None
    user_id: int | None = None
    channel_id: int

    integration: enums.Integration
    type: MessageType

    text: str


class MessageUpdate(BaseModel):
    integration: enums.Integration
    text: str | None = None


class SuccessPull(BaseModel):
    channel_id: int
    message_id: int
    status: MessageStatus


class SkippedPull(BaseModel):
    channel_id: int
    status: MessageStatus


class OrderResponse(BaseModel):
    created: list[SuccessPull] = Field(default=[])
    updated: list[SuccessPull] = Field(default=[])
    deleted: list[SuccessPull] = Field(default=[])
    skipped: list[SkippedPull] = Field(default=[])

    error: bool = Field(default=False)
    error_msg: str | None = Field(default=None)


class MessageResponse(BaseModel):
    status: MessageStatus
    channel_id: int


class MessagePaginationParams(pagination.PaginationParams):
    integration: enums.Integration
    channel_id: int | None = None
    order_id: int | None = None
    type: MessageType | None = None

    def apply_filter(self, query: Select) -> Select:
        query = query.where(Message.integration == self.integration)
        if self.channel_id:
            query = query.where(Message.channel_id == self.channel_id)
        if self.order_id:
            query = query.where(Message.order_id == self.order_id)
        if self.type:
            query = query.where(Message.type == self.type)
        return query
