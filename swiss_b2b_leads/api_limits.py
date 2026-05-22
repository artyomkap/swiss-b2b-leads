from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class ApiLimitEvent:
    provider: str
    event_type: str
    message: str
    status_code: Optional[int] = None
    error_code: str = ""
    severity: str = "warning"
    action_taken: str = "recorded"

    def to_dict(self) -> dict:
        return {
            "provider": self.provider,
            "event_type": self.event_type,
            "message": self.message,
            "status_code": self.status_code,
            "error_code": self.error_code,
            "severity": self.severity,
            "action_taken": self.action_taken,
            "detected_at": datetime.now().isoformat(),
        }


class ProviderLimitError(Exception):
    def __init__(
        self,
        provider: str,
        message: str,
        event_type: str = "unknown_error",
        status_code: Optional[int] = None,
        error_code: str = "",
    ):
        super().__init__(message)
        self.event = ApiLimitEvent(
            provider=provider,
            event_type=event_type,
            message=message,
            status_code=status_code,
            error_code=error_code,
            severity="critical" if event_type in {"quota_exceeded", "invalid_key"} else "warning",
            action_taken="source_disabled",
        )


def classify_api_error(message: str, status_code: Optional[int] = None) -> str:
    msg = (message or "").lower()
    if status_code == 401 or "invalid api key" in msg or "api key not valid" in msg:
        return "invalid_key"
    if status_code == 403 and any(k in msg for k in ["permission", "billing", "denied"]):
        return "invalid_key"
    if status_code == 429 or any(k in msg for k in ["rate limit", "too many requests", "too many"]):
        return "rate_limited"
    if any(k in msg for k in ["quota", "resource_exhausted", "credits", "no credits", "limit exceeded", "billing"]):
        return "quota_exceeded"
    if any(k in msg for k in ["permission denied", "forbidden"]):
        return "invalid_key"
    return "unknown_error"


def is_limit_event(event_type: str) -> bool:
    return event_type in {"quota_exceeded", "rate_limited", "invalid_key"}


def missing_key_event(provider: str) -> ApiLimitEvent:
    return ApiLimitEvent(
        provider=provider,
        event_type="missing",
        message=f"{provider} skipped because no API key is configured.",
        severity="warning",
        action_taken="source_skipped",
    )
