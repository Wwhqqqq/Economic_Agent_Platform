"""Async SQLAlchemy engine and session factory."""
from __future__ import annotations

import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "mysql+aiomysql://root:password@localhost:3306/agent_platform?charset=utf8mb4",
)

engine = create_async_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=int(os.getenv("DB_POOL_SIZE", "10")),
    max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "10")),
    echo=os.getenv("DB_ECHO", "false").lower() == "true",
)

AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@asynccontextmanager
async def session_scope() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def ping_mysql() -> dict:
    try:
        from sqlalchemy import text

        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "up", "url": DATABASE_URL.split("@")[-1] if "@" in DATABASE_URL else "configured"}
    except Exception as exc:
        return {"status": "down", "error": str(exc)}


async def init_db() -> None:
    """Create tables when migrations are not used (dev fallback)."""
    from app.db.models.base import Base
    import app.db.models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
