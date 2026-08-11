"""Seed users and system settings on startup."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

from sqlalchemy import select

from app.core.database import session_scope
from app.db.models.system import SystemSetting
from app.db.models.user import User
from app.db.models.membership import MembershipCode
from app.services.auth import hash_password


DEFAULT_SETTINGS = {
    "quota.regular.max_sessions": 20,
    "quota.member.max_sessions": 500,
    "quota.regular.max_documents": 10,
    "quota.member.max_documents": 200,
    "quota.regular.max_file_mb": 5,
    "quota.member.max_file_mb": 20,
    "quota.regular.daily_messages": 100,
    "quota.member.daily_messages": 2000,
    "quota.regular.max_long_term_memories": 0,
    "quota.member.max_long_term_memories": 500,
    "membership.trial.enabled": False,
    "membership.trial.duration_days": 7,
    "membership.pricing.monthly_cents": 5900,
    "membership.pricing.yearly_cents": 49900,
    "feature.code_executor_member_only": True,
}


async def seed_initial_data() -> None:
    if os.getenv("SKIP_DB_SEED", "false").lower() == "true":
        return

    async with session_scope() as db:
        for key, value in DEFAULT_SETTINGS.items():
            existing = await db.execute(select(SystemSetting).where(SystemSetting.key == key))
            if existing.scalar_one_or_none() is None:
                db.add(SystemSetting(key=key, value_json=json.dumps(value)))

        users_to_seed = [
            # 原有测试账号
            ("test_regular", "Test123456", "regular", None),
            ("test_member", "Test123456", "member", datetime(2099, 12, 31, tzinfo=timezone.utc)),
            # 演示账号
            ("demo_regular", "Test123456", "regular", None),
            ("demo_member", "Test123456", "member", datetime(2099, 12, 31, tzinfo=timezone.utc)),
            # 业务命名账号
            ("user_regular", "Test123456", "regular", None),
            ("user_member", "Test123456", "member", datetime(2027, 6, 30, tzinfo=timezone.utc)),
            # 过期会员（登录时自动降级为普通用户）
            ("expired_member", "Test123456", "member", datetime(2020, 1, 1, tzinfo=timezone.utc)),
        ]
        for username, password, user_type, expires in users_to_seed:
            result = await db.execute(select(User).where(User.username == username))
            if result.scalar_one_or_none() is None:
                db.add(
                    User(
                        username=username,
                        password_hash=hash_password(password),
                        user_type=user_type,
                        membership_expires_at=expires,
                        status="active",
                    )
                )

        code_result = await db.execute(
            select(MembershipCode).where(MembershipCode.code == "TEST-MEMBER-2026")
        )
        if code_result.scalar_one_or_none() is None:
            db.add(
                MembershipCode(
                    code="TEST-MEMBER-2026",
                    duration_days=365,
                    max_uses=100,
                    use_count=0,
                )
            )
