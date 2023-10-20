from datetime import datetime
from typing import AsyncGenerator

from sqlalchemy import MetaData, BigInteger, text, event
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.core import config


class Base(DeclarativeBase):
    pass


metadata = MetaData()


class TimeStampMixin(Base):
    __abstract__ = True
    id: Mapped[int] = mapped_column(BigInteger(), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(nullable=True)


@event.listens_for(TimeStampMixin, "before_update")
def receive_before_update(mapper, connection, target):
    target.updated_at = datetime.utcnow()


engine = create_async_engine(url=config.app.db_url_asyncpg, echo=True)
async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session
