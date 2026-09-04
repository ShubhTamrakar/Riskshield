"""
Input sanitization and prompt injection guard.

SQLAlchemy already uses parameterized queries, so SQL injection is handled
at the ORM layer. This module handles:
  1. Stripping non-printable / control characters from string inputs
  2. Truncating oversized strings to safe limits
  3. Stripping adversarial LLM instruction patterns from free-text fields
     before they are forwarded to the AI investigator
"""
import re
from typing import Any

# Maximum length for any individual string field (characters)
MAX_FIELD_LENGTH = 1024

# Patterns that indicate prompt injection attempts.
# Applied to any free-text field that feeds into the LLM.
_INJECTION_PATTERNS = re.compile(
    r"""
    (ignore\s+(all\s+)?previous\s+instructions?)|
    (disregard\s+(all\s+)?prior)|
    (system\s+prompt)|
    (you\s+are\s+now)|
    (act\s+as\s+(?:a\s+)?(?:different|new|unrestricted))|
    (jailbreak)|
    (do\s+not\s+follow)|
    (override\s+(your\s+)?instructions?)|
    (forget\s+(all\s+)?previous\s+instructions?)|
    (<\s*\/?(?:system|user|assistant)\s*>)|
    (\[INST\]|\[\/INST\])|
    (\#\#\#\s*Instruction)|
    (CONFIDENTIAL\s+SYSTEM\s+PROMPT)
    """,
    re.IGNORECASE | re.VERBOSE,
)

# Control chars except common whitespace (\t, \n, \r)
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def sanitize_string(value: str, max_length: int = MAX_FIELD_LENGTH) -> str:
    """Remove control characters and truncate to max_length."""
    if not isinstance(value, str):
        return value
    value = _CONTROL_CHARS.sub("", value)
    return value[:max_length]


def guard_prompt_injection(text: str) -> str:
    """Remove known prompt-injection patterns from text destined for LLM."""
    if not isinstance(text, str):
        return text
    cleaned = _INJECTION_PATTERNS.sub("[REDACTED]", text)
    return cleaned[:MAX_FIELD_LENGTH]


def sanitize_dict(data: dict[str, Any], max_depth: int = 5) -> dict[str, Any]:
    """Recursively sanitize all string values in a dict."""
    if max_depth <= 0:
        return {}
    out: dict[str, Any] = {}
    for k, v in data.items():
        if isinstance(v, str):
            out[k] = sanitize_string(v)
        elif isinstance(v, dict):
            out[k] = sanitize_dict(v, max_depth - 1)
        elif isinstance(v, list):
            out[k] = [sanitize_string(i) if isinstance(i, str) else i for i in v]
        else:
            out[k] = v
    return out
