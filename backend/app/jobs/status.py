from __future__ import annotations

from enum import Enum


class JobStatus(str, Enum):
    PENDING = "pending"
    PARSING = "parsing"
    READY = "ready"
    FAILED = "failed"
    NEEDS_REVIEW = "needs_review"


class ParseStatus(str, Enum):
    PENDING = "pending"
    PARSING = "parsing"
    READY = "ready"
    FAILED = "failed"
    NEEDS_REVIEW = "needs_review"
