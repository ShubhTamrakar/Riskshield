"""
Consistent error envelope for all 4xx / 5xx responses.

Every error response follows this schema:
{
  "error":      "short_snake_case_code",
  "message":    "Human-readable description",
  "request_id": "uuid",
  "timestamp":  "2024-01-01T00:00:00Z"
}

Internal details (stack traces, SQL errors) are NEVER exposed in production.
"""
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel


class ErrorResponse(BaseModel):
    error: str
    message: str
    request_id: Optional[str] = None
    timestamp: str = ""

    @classmethod
    def build(cls, error: str, message: str, request_id: Optional[str] = None) -> "ErrorResponse":
        return cls(
            error=error,
            message=message,
            request_id=request_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
