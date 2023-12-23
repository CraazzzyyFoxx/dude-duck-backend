from datetime import datetime
from typing import AsyncGenerator

from sqlalchemy import BigInteger, DateTime, create_engine, func
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from src.core import config


class Base(DeclarativeBase):
    def to_dict(self):
        return {c.name: getattr(self, c.name, None) for c in self.__table__.columns}


class TimeStampMixin(Base):
    __abstract__ = True

    id: Mapped[int] = mapped_column(BigInteger(), primary_key=True, sort_order=-1000)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), sort_order=-999, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True, sort_order=-998, onupdate=func.now()
    )


async_engine = create_async_engine(url=config.app.db_url_asyncpg)
engine = create_engine(url=config.app.db_url)
session_maker = sessionmaker(engine, class_=Session, expire_on_commit=False)
async_session_maker = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session
