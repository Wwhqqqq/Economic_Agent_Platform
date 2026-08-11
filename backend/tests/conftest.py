"""Pytest fixtures for membership tests."""
from __future__ import annotations

import os

# Environment before app imports
os.environ["AUTH_ENABLED"] = "true"
os.environ["SKIP_DB_SEED"] = "true"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["MEMBERSHIP_WEBHOOK_SECRET"] = "test-webhook-secret"

import sqlalchemy.ext.asyncio.engine as _engine_mod

_orig_create_async_engine = _engine_mod.create_async_engine


def _patched_create_async_engine(url, **kw):
    if str(url).startswith("sqlite"):
        kw.pop("pool_size", None)
        kw.pop("max_overflow", None)
    return _orig_create_async_engine(url, **kw)


_engine_mod.create_async_engine = _patched_create_async_engine

from datetime import datetime, timezone

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.db.models  # noqa: F401 — register models
from app.core.database import get_db
from app.db.models.base import Base
from app.db.models.membership import MembershipCode
from app.db.models.user import User
from app.services.auth import hash_password
from main import app


@pytest_asyncio.fixture
async def db_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine):
    session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
        await session.commit()


@pytest_asyncio.fixture
async def test_users(db_session: AsyncSession):
    regular = User(
        id=1,
        username="test_regular_py",
        password_hash=hash_password("Test123456"),
        user_type="regular",
        status="active",
    )
    member = User(
        id=2,
        username="test_member_py",
        password_hash=hash_password("Test123456"),
        user_type="member",
        membership_expires_at=datetime(2099, 12, 31, tzinfo=timezone.utc),
        status="active",
    )
    db_session.add(regular)
    await db_session.flush()
    db_session.add(member)
    await db_session.flush()
    db_session.add(
        MembershipCode(code="TEST-MEMBER-2026", duration_days=30, max_uses=100, use_count=0)
    )
    await db_session.flush()
    await db_session.refresh(regular)
    await db_session.refresh(member)
    return {"regular": regular, "member": member}


@pytest_asyncio.fixture
async def client(db_engine):
    session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            yield session
            await session.commit()

    app.dependency_overrides[get_db] = override_get_db

    from app.skills.registry import skill_registry
    if skill_registry.skill_count == 0:
        skill_registry.load_from_directory()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
