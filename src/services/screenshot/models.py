from datetime import datetime

from pydantic import BaseModel, ConfigDict, HttpUrl
from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core import db
from src.services.order import models as order_models
from src.services.auth import models as auth_models


class Screenshot(db.TimeStampMixin):
    __tablename__ = "screenshot"

    source: Mapped[str] = mapped_column(String(), nullable=False)
    url: Mapped[str] = mapped_column(String(), nullable=False)
    order_id: Mapped[int] = mapped_column(ForeignKey("order.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    user: Mapped[auth_models.User] = relationship()
    order: Mapped[order_models.Order] = relationship(back_populates="screenshots")


class ScreenshotRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime

    source: str
    url: HttpUrl
    order_id: int


class ScreenshotCreate(BaseModel):
    url: HttpUrl
