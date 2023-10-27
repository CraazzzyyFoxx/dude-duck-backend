from datetime import datetime
from typing import AsyncGenerator

from sqlalchemy import BigInteger, text, event, create_engine, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker, Session
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from src.core import config


class Base(DeclarativeBase):

    def to_dict(self):
        return {c.name: getattr(self, c.name, None) for c in self.__table__.columns}  # type: ignore


class TimeStampMixin(Base):
    __abstract__ = True

    id: Mapped[int] = mapped_column(BigInteger(), primary_key=True, sort_order=-1000)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"), sort_order=-999)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True, sort_order=-998)


@event.listens_for(TimeStampMixin, "before_update")
def receive_before_update(mapper, connection, target):
    target.updated_at = datetime.utcnow()


async_engine = create_async_engine(url=config.app.db_url_asyncpg)
engine = create_engine(url=config.app.db_url)
session_maker = sessionmaker(engine, class_=Session, expire_on_commit=False)
async_session_maker = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session
