"""Redeem code validation and consumption."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.membership import MembershipCode, MembershipRedemption
from app.db.models.user import User
from app.services.membership_service import activate_membership


class RedeemError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


async def redeem_code(db: AsyncSession, user: User, raw_code: str) -> datetime:
    code_str = raw_code.strip().upper()
    if not code_str:
        raise RedeemError("INVALID_REDEEM_CODE", "请输入兑换码")

    result = await db.execute(
        select(MembershipCode).where(func.upper(MembershipCode.code) == code_str)
    )
    code_row = result.scalar_one_or_none()
    if not code_row:
        raise RedeemError("INVALID_REDEEM_CODE", "兑换码无效")

    now = datetime.now(timezone.utc)
    if code_row.expires_at:
        exp = code_row.expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if exp < now:
            raise RedeemError("INVALID_REDEEM_CODE", "兑换码已过期")

    if code_row.use_count >= code_row.max_uses:
        raise RedeemError("REDEEM_CODE_USED", "兑换码已被使用")

    # One redemption per user per code when max_uses > 1 still allowed globally
    prior = await db.execute(
        select(MembershipRedemption).where(
            MembershipRedemption.code_id == code_row.id,
            MembershipRedemption.user_id == user.id,
        )
    )
    if prior.scalar_one_or_none():
        raise RedeemError("REDEEM_CODE_USED", "您已使用过该兑换码")

    expires = await activate_membership(
        db,
        user,
        duration_days=code_row.duration_days,
        plan="redeem",
        source="redeem",
        external_order_id=f"redeem-{code_row.id}-{user.id}-{int(now.timestamp())}",
        amount_cents=0,
    )

    code_row.use_count += 1
    db.add(
        MembershipRedemption(
            code_id=code_row.id,
            user_id=user.id,
        )
    )
    await db.flush()
    return expires
