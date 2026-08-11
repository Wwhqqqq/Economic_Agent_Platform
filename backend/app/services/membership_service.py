"""Membership activation, status, and pricing."""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.catalog import normalize_execution_mode
from app.db.models.membership import MembershipOrder
from app.db.models.system import SystemSetting
from app.db.models.user import User
from app.services.membership_gate import MEMBER_ONLY_SKILLS, skill_requires_membership
from app.services.quota_service import get_quota_snapshot

PLAN_DURATIONS = {
    "trial_7d": 7,
    "monthly": 30,
    "yearly": 365,
    "redeem": 0,  # set from code
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def compute_expires_after(
    current_expires: Optional[datetime],
    duration_days: int,
    *,
    is_active_member: bool,
) -> datetime:
    base = _now()
    if is_active_member and current_expires:
        exp = current_expires
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if exp > base:
            base = exp
    return base + timedelta(days=duration_days)


async def _get_setting(db: AsyncSession, key: str, default: Any) -> Any:
    result = await db.execute(select(SystemSetting).where(SystemSetting.key == key))
    row = result.scalar_one_or_none()
    if not row:
        return default
    try:
        return json.loads(row.value_json)
    except json.JSONDecodeError:
        return default


async def activate_membership(
    db: AsyncSession,
    user: User,
    *,
    duration_days: int,
    plan: str,
    source: str,
    external_order_id: str,
    amount_cents: int = 0,
) -> datetime:
    is_active = user.user_type == "member" and (
        user.membership_expires_at is None
        or (
            user.membership_expires_at.replace(tzinfo=timezone.utc)
            if user.membership_expires_at.tzinfo is None
            else user.membership_expires_at
        )
        > _now()
    )
    expires = compute_expires_after(user.membership_expires_at, duration_days, is_active_member=is_active)
    user.user_type = "member"
    user.membership_expires_at = expires

    order = MembershipOrder(
        user_id=user.id,
        external_order_id=external_order_id,
        plan=plan,
        amount_cents=amount_cents,
        paid_at=_now(),
        expires_after=expires,
        source=source,
    )
    db.add(order)
    await db.flush()
    return expires


async def get_membership_status(db: AsyncSession, user: User) -> dict[str, Any]:
    from app.schemas.user_context import UserContext

    ctx = UserContext(
        user_id=user.id,
        username=user.username,
        user_type=user.user_type,
        membership_expires_at=user.membership_expires_at,
    )
    is_member = ctx.is_member

    days_remaining: Optional[int] = None
    if is_member and user.membership_expires_at:
        exp = user.membership_expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        delta = exp - _now()
        days_remaining = max(0, delta.days)

    # Detect trial: latest order with plan trial_7d and no paid amount
    is_trial = False
    if is_member:
        result = await db.execute(
            select(MembershipOrder)
            .where(MembershipOrder.user_id == user.id, MembershipOrder.plan == "trial_7d")
            .order_by(MembershipOrder.created_at.desc())
            .limit(1)
        )
        trial_order = result.scalar_one_or_none()
        if trial_order and trial_order.amount_cents == 0:
            is_trial = True

    tier = "member" if is_member else "regular"
    if is_member:
        execution_modes = ["adaptive", "reasoning_action", "task_orchestration"]
        skills = ["document_analysis", "data_visualization", "financial_audit"]
    else:
        execution_modes = ["adaptive"]
        skills = ["document_analysis"]

    monthly_cents = int(await _get_setting(db, "membership.pricing.monthly_cents", 5900))
    yearly_cents = int(await _get_setting(db, "membership.pricing.yearly_cents", 49900))

    upgrade_url_template = os.getenv("MEMBERSHIP_UPGRADE_URL", "")
    upgrade_url = None
    if upgrade_url_template:
        upgrade_url = upgrade_url_template.replace("{user_id}", str(user.id))

    return {
        "user_type": user.user_type if is_member else "regular",
        "is_member": is_member,
        "membership_expires_at": (
            user.membership_expires_at.isoformat() if user.membership_expires_at and is_member else None
        ),
        "is_trial": is_trial,
        "days_remaining": days_remaining,
        "benefits": {
            "execution_modes": execution_modes,
            "skills": skills,
            "member_knowledge": is_member,
            "personal_llm": is_member,
        },
        "plans": [
            {
                "id": "monthly",
                "name": "会员月卡",
                "price_cents": monthly_cents,
                "duration_days": 30,
            },
            {
                "id": "yearly",
                "name": "会员年卡",
                "price_cents": yearly_cents,
                "duration_days": 365,
                "recommended": True,
            },
        ],
        "upgrade_url": upgrade_url,
    }


async def apply_registration_trial(db: AsyncSession, user: User) -> bool:
    enabled = await _get_setting(db, "membership.trial.enabled", True)
    if not enabled:
        return False
    days = int(await _get_setting(db, "membership.trial.duration_days", 7))
    await activate_membership(
        db,
        user,
        duration_days=days,
        plan="trial_7d",
        source="trial",
        external_order_id=f"trial-{user.id}-{int(_now().timestamp())}",
        amount_cents=0,
    )
    return True


def enrich_skill_membership(skill_dict: dict) -> dict:
    name = skill_dict.get("name", "")
    skill_dict["membership_required"] = skill_requires_membership(name)
    return skill_dict
