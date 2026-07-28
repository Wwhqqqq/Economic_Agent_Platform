"""Shared field validators for auth (register / login)."""
from __future__ import annotations

import re

USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{3,64}$")
PASSWORD_RE = re.compile(r"^[A-Za-z0-9_]{6,128}$")
EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
VERIFICATION_CODE_RE = re.compile(r"^[0-9]{4}$")


def validate_username(value: str) -> tuple[bool, str | None]:
    if not value or not value.strip():
        return False, "请输入用户名"
    if not USERNAME_RE.match(value):
        if len(value) < 3 or len(value) > 64:
            return False, "用户名长度为 3–64 个字符"
        return False, "用户名只能包含字母、数字和下划线"
    return True, None


def validate_email(value: str) -> tuple[bool, str | None]:
    if not value or not value.strip():
        return False, "请输入邮箱地址"
    if not EMAIL_RE.match(value.strip()):
        return False, "请输入有效的邮箱地址"
    return True, None


def validate_password(value: str) -> tuple[bool, str | None]:
    if not value:
        return False, "请输入密码"
    if not PASSWORD_RE.match(value):
        if len(value) < 6:
            return False, "密码至少 6 位"
        return False, "密码只能包含字母、数字和下划线"
    return True, None


def validate_verification_code(value: str) -> tuple[bool, str | None]:
    if not value or not value.strip():
        return False, "请输入验证码"
    if not VERIFICATION_CODE_RE.match(value.strip()):
        return False, "请输入 4 位数字验证码"
    return True, None
