"""Membership system tests — gate, quota, API."""
from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone

import pytest

from app.schemas.user_context import UserContext
from app.services.membership_gate import (
    MembershipRequiredError,
    assert_membership_for_explicit_mode,
    assert_membership_for_resolved,
    assert_membership_for_skill,
    skill_requires_membership,
)
from app.agent.orchestrator import AgentOrchestrator


def _regular() -> UserContext:
    return UserContext(user_id=1, username="regular", user_type="regular")


def _member() -> UserContext:
    return UserContext(
        user_id=2,
        username="member",
        user_type="member",
        membership_expires_at=datetime(2099, 12, 31, tzinfo=timezone.utc),
    )


class TestMembershipGate:
    def test_skill_requires_membership(self):
        assert skill_requires_membership("financial_audit") is True
        assert skill_requires_membership("document_analysis") is False

    def test_regular_blocked_plan_mode(self):
        with pytest.raises(MembershipRequiredError):
            assert_membership_for_explicit_mode(_regular(), "task_orchestration")

    def test_regular_blocked_medium_mode(self):
        with pytest.raises(MembershipRequiredError):
            assert_membership_for_explicit_mode(_regular(), "reasoning_action")

    def test_regular_allowed_adaptive(self):
        assert_membership_for_explicit_mode(_regular(), "adaptive") is None

    def test_regular_blocked_skill(self):
        with pytest.raises(MembershipRequiredError):
            assert_membership_for_skill(_regular(), "financial_audit")

    def test_member_allowed_plan(self):
        assert_membership_for_resolved(
            _member(),
            mode="task_orchestration",
            skill=None,
            expert_id=None,
            requested_mode="task_orchestration",
        ) is None

    def test_regular_blocked_resolved_plan(self):
        with pytest.raises(MembershipRequiredError):
            assert_membership_for_resolved(
                _regular(),
                mode="task_orchestration",
                skill=None,
                expert_id=None,
                requested_mode=None,
            )


class TestOrchestratorRouting:
    def setup_method(self):
        self.orchestrator = AgentOrchestrator()

    def test_regular_auto_routes_to_react_only(self):
        mode = self.orchestrator._select_mode("请做财务审计报告", "adaptive", user=_regular())
        assert mode == "reasoning_action"

    def test_member_auto_can_route_to_plan(self):
        mode = self.orchestrator._select_mode("请做财务审计报告", "adaptive", user=_member())
        assert mode == "task_orchestration"

    def test_member_auto_can_route_to_debate(self):
        mode = self.orchestrator._select_mode("请组织委员会辩论", "adaptive", user=_member())
        assert mode == "collaborative_decision"


def _sign_webhook(body: bytes, secret: str) -> str:
    sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return f"sha256={sig}"


@pytest.mark.asyncio
async def test_membership_api_flow(client, db_session, test_users):
    """Integration: status, redeem, webhook."""
    import os
    from app.services.auth import create_token

    regular = test_users["regular"]
    member = test_users["member"]

    regular_token = create_token(regular)
    member_token = create_token(member)

    # Status — regular
    resp = await client.get(
        "/api/membership/status",
        headers={"Authorization": f"Bearer {regular_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_member"] is False
    assert "adaptive" in data["benefits"]["execution_modes"]

    # Status — member
    resp = await client.get(
        "/api/membership/status",
        headers={"Authorization": f"Bearer {member_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["is_member"] is True

    # Skills list includes membership_required
    resp = await client.get("/api/skills")
    assert resp.status_code == 200
    skills = resp.json()["skills"]
    audit = next(s for s in skills if s["name"] == "financial_audit")
    assert audit["membership_required"] is True

    # Skill execute — regular blocked
    resp = await client.post(
        "/api/skills/financial_audit/execute",
        headers={"Authorization": f"Bearer {regular_token}"},
        json={"input": "test", "session_id": "s1"},
    )
    assert resp.status_code == 403
    detail = resp.json()["detail"]
    if isinstance(detail, dict):
        assert detail.get("code") == "MEMBERSHIP_REQUIRED"

    # Redeem code
    resp = await client.post(
        "/api/membership/redeem",
        headers={"Authorization": f"Bearer {regular_token}"},
        json={"code": "TEST-MEMBER-2026"},
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is True

    # Webhook
    import app.api.membership as membership_api
    secret = "test-webhook-secret"
    membership_api.WEBHOOK_SECRET = secret
    payload = {
        "event": "payment.success",
        "order_id": "order-test-001",
        "user_id": regular.id,
        "plan": "monthly",
        "amount_cents": 5900,
    }
    body = json.dumps(payload).encode()
    resp = await client.post(
        "/api/membership/webhook",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-Webhook-Signature": _sign_webhook(body, secret),
        },
    )
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
