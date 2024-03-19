from datetime import UTC, datetime, timedelta

from sqlalchemy import delete

from src import models
from src.core import db


async def remove_expired_tokens():
    async with db.session_maker() as session:
        await session.execute(
            delete(models.RefreshToken).where(models.RefreshToken.created_at < datetime.now(UTC) - timedelta(days=30))
        )
        await session.commit()
