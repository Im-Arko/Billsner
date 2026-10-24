"""Async SQLAlchemy engine and session factory."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import event
from sqlalchemy.engine import make_url
from pathlib import Path

from app.config import get_settings

settings = get_settings()

def create_database_engine(url: str, **kwargs):
    is_sqlite = url.startswith("sqlite")
    if is_sqlite:
        database = make_url(url).database
        if database and database != ":memory:":
            Path(database).parent.mkdir(parents=True, exist_ok=True)
        kwargs["connect_args"] = {"timeout": 30}
    engine = create_async_engine(url, pool_pre_ping=True, **kwargs)
    if is_sqlite:
        @event.listens_for(engine.sync_engine, "connect")
        def configure_sqlite(connection, _):
            cursor = connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.close()
    return engine


engine = create_database_engine(settings.DATABASE_URL, echo=settings.DEBUG)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
