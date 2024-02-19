from sqlalchemy import Boolean, Enum,  String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.core import db, enums

__all__ = ("RenderConfig",)


class RenderConfig(db.TimeStampMixin):
    __tablename__ = "integration_render_config"
    __table_args__ = (UniqueConstraint("name", "lang", "integration", name="idx_name_lang"),)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    lang: Mapped[str] = mapped_column(String(255), nullable=False)
    integration: Mapped[enums.Integration] = mapped_column(Enum(enums.Integration), nullable=False)
    binary: Mapped[str] = mapped_column(Text(), nullable=False)
    allow_separator_top: Mapped[bool] = mapped_column(Boolean, nullable=False)
    separator: Mapped[str] = mapped_column(String(255), nullable=False)
