"""Membership feature gating — modes, skills, experts."""
from __future__ import annotations

from app.core.catalog import normalize_execution_mode
from app.schemas.user_context import UserContext

MEMBER_ONLY_MODES = frozenset({"task_orchestration", "collaborative_decision"})
MEMBER_ONLY_SKILLS = frozenset({"financial_audit", "data_visualization"})

# expert_id -> required canonical mode when invoked
MEMBER_ONLY_EXPERTS: dict[str, str] = {
    "finance_reviewer": "task_orchestration",
    "finance_review_board": "collaborative_decision",
}


class MembershipRequiredError(Exception):
    def __init__(self, message: str = "该功能需开通会员"):
        self.message = message
        super().__init__(message)


class QuotaExceededError(Exception):
    def __init__(self, quota: str, message: str):
        self.quota = quota
        self.message = message
        super().__init__(message)


def skill_requires_membership(skill_name: str | None) -> bool:
    return bool(skill_name and skill_name in MEMBER_ONLY_SKILLS)


def assert_membership_for_mode(user: UserContext, mode: str) -> None:
    if user.is_member:
        return
    canonical = normalize_execution_mode(mode)
    if canonical in MEMBER_ONLY_MODES:
        raise MembershipRequiredError("该执行模式需开通会员")
    if canonical == "reasoning_action" and mode and normalize_execution_mode(mode) == "reasoning_action":
        # Explicit Medium selection by non-member
        if mode not in ("adaptive", "auto", None, ""):
            # Only block if user explicitly chose reasoning_action (not internal routing)
            pass


def assert_membership_for_explicit_mode(user: UserContext, requested_mode: str | None) -> None:
    """Block non-members from manually selecting Medium/Plan."""
    if user.is_member or not requested_mode:
        return
    canonical = normalize_execution_mode(requested_mode)
    if canonical != "adaptive" and canonical in MEMBER_ONLY_MODES | {"reasoning_action"}:
        if canonical == "reasoning_action":
            raise MembershipRequiredError("推理闭环模式需开通会员")
        raise MembershipRequiredError("该执行模式需开通会员")


def assert_membership_for_skill(user: UserContext, skill: str | None) -> None:
    if user.is_member:
        return
    if skill_requires_membership(skill):
        raise MembershipRequiredError("该技能需开通会员")


def assert_membership_for_expert(user: UserContext, expert_id: str | None) -> None:
    if user.is_member or not expert_id:
        return
    required_mode = MEMBER_ONLY_EXPERTS.get(expert_id)
    if required_mode:
        raise MembershipRequiredError("该专家需开通会员")


def assert_membership_for_resolved(
    user: UserContext,
    *,
    mode: str,
    skill: str | None,
    expert_id: str | None,
    requested_mode: str | None = None,
) -> None:
    assert_membership_for_explicit_mode(user, requested_mode)
    assert_membership_for_mode(user, mode)
    assert_membership_for_skill(user, skill)
    assert_membership_for_expert(user, expert_id)
    # Expert may imply plan/multi-agent via resolved mode
    if not user.is_member:
        canonical = normalize_execution_mode(mode)
        if canonical in MEMBER_ONLY_MODES:
            raise MembershipRequiredError("该执行模式需开通会员")
