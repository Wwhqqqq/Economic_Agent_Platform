"""Membership REST API."""
from __future__ import annotations

import hashlib
import hmac
import json
import os
from datetime import datetime, timezone
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.db.models.membership import MembershipOrder
from app.db.models.user import User
from app.schemas.user_context import UserContext
from app.services.audit_log import log_action
from app.services.auth import get_current_user, get_user_by_id
from app.services.membership_service import PLAN_DURATIONS, activate_membership, get_membership_status
from app.services.quota_service import get_quota_snapshot, quota_http_exception
from app.services.membership_gate import QuotaExceededError
from app.services.redeem_service import RedeemError, redeem_code

router = APIRouter(prefix="/api/membership", tags=["membership"])

WEBHOOK_SECRET = os.getenv("MEMBERSHIP_WEBHOOK_SECRET", "")


class RedeemRequest(BaseModel):
    code: str = Field(min_length=1, max_length=64)


class WebhookPayload(BaseModel):
    event: Literal["payment.success"]
    order_id: str
    user_id: int
    plan: Literal["monthly", "yearly", "trial_7d"]
    amount_cents: int = 0
    paid_at: Optional[str] = None


def _verify_webhook_signature(body: bytes, signature_header: str) -> bool:
    if not WEBHOOK_SECRET:
        return False
    if not signature_header.startswith("sha256="):
        return False
    expected = hmac.new(WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()
    provided = signature_header[7:]
    return hmac.compare_digest(expected, provided)


@router.get("/status")
async def membership_status(
    user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not user.user_id:
        raise HTTPException(status_code=401, detail="未登录")
    db_user = await get_user_by_id(db, user.user_id)
    if not db_user:
        raise HTTPException(status_code=401, detail="用户不存在")
    return await get_membership_status(db, db_user)


@router.get("/quota")
async def membership_quota(
    user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not user.user_id:
        raise HTTPException(status_code=401, detail="未登录")
    tier = "member" if user.is_member else "regular"
    return await get_quota_snapshot(db, user.user_id, tier)


@router.post("/redeem")
async def membership_redeem(
    req: RedeemRequest,
    user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not user.user_id:
        raise HTTPException(status_code=401, detail="未登录")
    db_user = await get_user_by_id(db, user.user_id)
    if not db_user:
        raise HTTPException(status_code=401, detail="用户不存在")
    try:
        expires = await redeem_code(db, db_user, req.code)
        await db.commit()
    except RedeemError as exc:
        raise HTTPException(
            status_code=400,
            detail={"code": exc.code, "message": exc.message},
        ) from exc

    log_action("membership.redeemed", user.username, {"code_prefix": req.code[:4]})
    return {
        "success": True,
        "membership_expires_at": expires.isoformat(),
        "message": f"兑换成功，会员有效期至 {expires.date()}",
        "user_type": "member",
    }


@router.post("/webhook")
async def membership_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    body = await request.body()
    sig = request.headers.get("X-Webhook-Signature", "")
    if not _verify_webhook_signature(body, sig):
        raise HTTPException(
            status_code=401,
            detail={"code": "WEBHOOK_SIGNATURE_INVALID", "message": "签名校验失败"},
        )

    try:
        payload = WebhookPayload.model_validate(json.loads(body))
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid payload") from exc

    if payload.event != "payment.success":
        return {"ok": True, "skipped": True}

    existing = await db.execute(
        select(MembershipOrder).where(
            MembershipOrder.external_order_id == payload.order_id
        )
    )
    if existing.scalar_one_or_none():
        return {"ok": True, "duplicate": True}

    db_user = await get_user_by_id(db, payload.user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    duration = PLAN_DURATIONS.get(payload.plan, 30)
    expires = await activate_membership(
        db,
        db_user,
        duration_days=duration,
        plan=payload.plan,
        source="webhook",
        external_order_id=payload.order_id,
        amount_cents=payload.amount_cents,
    )
    await db.commit()
    log_action("membership.activated", db_user.username, {"plan": payload.plan, "order_id": payload.order_id})
    return {"ok": True, "membership_expires_at": expires.isoformat()}


@router.get("/orders")
async def membership_orders(
    user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not user.user_id:
        raise HTTPException(status_code=401, detail="未登录")
    result = await db.execute(
        select(MembershipOrder)
        .where(MembershipOrder.user_id == user.user_id)
        .order_by(MembershipOrder.created_at.desc())
        .limit(20)
    )
    orders = result.scalars().all()
    return {
        "orders": [
            {
                "id": o.id,
                "plan": o.plan,
                "amount_cents": o.amount_cents,
                "paid_at": o.paid_at.isoformat() if o.paid_at else None,
                "expires_after": o.expires_after.isoformat() if o.expires_after else None,
                "source": o.source,
            }
            for o in orders
        ]
    }
