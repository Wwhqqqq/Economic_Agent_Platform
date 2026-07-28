"""Email delivery for verification codes."""
from __future__ import annotations

import logging
import os
import smtplib
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)

SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USER or "noreply@agent-platform.local")
SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
EMAIL_DEV_CONSOLE = os.getenv("EMAIL_DEV_CONSOLE", "true").lower() == "true"


def smtp_configured() -> bool:
    return bool(SMTP_HOST and SMTP_FROM)


async def send_verification_email(to_email: str, code: str) -> None:
    """Send 4-digit registration verification code."""
    subject = "【企业智能体工作台】注册验证码"
    body = f"{code}\n验证码 60 秒内有效"

    if smtp_configured():
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = SMTP_FROM
        msg["To"] = to_email
        try:
            if SMTP_USE_TLS:
                with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
                    server.starttls()
                    if SMTP_USER and SMTP_PASSWORD:
                        server.login(SMTP_USER, SMTP_PASSWORD)
                    server.sendmail(SMTP_FROM, [to_email], msg.as_string())
            else:
                with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
                    if SMTP_USER and SMTP_PASSWORD:
                        server.login(SMTP_USER, SMTP_PASSWORD)
                    server.sendmail(SMTP_FROM, [to_email], msg.as_string())
            return
        except Exception as exc:
            logger.error("SMTP send failed for %s: %s", to_email, exc)
            raise RuntimeError("邮件发送失败，请稍后重试") from exc

    if EMAIL_DEV_CONSOLE:
        logger.info("[DEV] Verification email to %s (check server console)", to_email)
        print(f"\n{'=' * 48}\n[DEV 注册验证码] {to_email}\n验证码: {code}\n有效期: 60 秒\n{'=' * 48}\n")
        return

    raise RuntimeError("邮件服务未配置，无法发送验证码")
