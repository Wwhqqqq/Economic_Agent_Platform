"""User context passed through request lifecycle."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional


@dataclass
class UserContext:
    user_id: int
    username: str
    user_type: str  # regular | member
    membership_expires_at: Optional[datetime] = None

    @property
    def is_member(self) -> bool:
        if self.user_type != "member":
            return False
        if self.membership_expires_at is None:
            return True
        now = datetime.now(timezone.utc)
        exp = self.membership_expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        return exp > now

    @classmethod
    def anonymous(cls) -> "UserContext":
        return cls(user_id=0, username="anonymous", user_type="regular")
