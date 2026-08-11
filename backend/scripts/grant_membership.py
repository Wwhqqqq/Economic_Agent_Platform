"""Grant membership to a user — ops CLI."""
from __future__ import annotations

import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy import select

from app.core.database import session_scope
from app.db.models.user import User
from app.services.membership_service import activate_membership


async def main(username: str, days: int, plan: str) -> None:
    async with session_scope() as db:
        result = await db.execute(select(User).where(User.username == username))
        user = result.scalar_one_or_none()
        if not user:
            print(f"User not found: {username}")
            sys.exit(1)
        expires = await activate_membership(
            db,
            user,
            duration_days=days,
            plan=plan,
            source="admin_script",
            external_order_id=f"manual-{user.id}-{days}d",
            amount_cents=0,
        )
        print(f"Granted {days}d membership to {username}, expires {expires.isoformat()}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Grant membership to user")
    parser.add_argument("--user", required=True, help="Username")
    parser.add_argument("--days", type=int, default=30, help="Duration days")
    parser.add_argument("--plan", default="monthly", help="Plan id for records")
    args = parser.parse_args()
    asyncio.run(main(args.user, args.days, args.plan))
