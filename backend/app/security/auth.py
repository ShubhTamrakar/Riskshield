"""
API Key authentication and role-based access control.

Security design:
- The API key is never stored in plaintext. Only its SHA-256 hash is kept in config.
- Comparison uses hmac.compare_digest() to prevent timing attacks.
- Roles (viewer, analyst, admin) are injected via X-Role header, which in production
  should be set by a trusted reverse proxy after the key check, never trusted from
  untrusted clients directly. In development, the header is accepted as-is.
- When API_KEY_HASH is empty, auth is skipped (development convenience).
"""
from typing import Optional
from fastapi import Depends, HTTPException, Security, status
from fastapi.security.api_key import APIKeyHeader

from app.core.config import settings

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
_role_header = APIKeyHeader(name="X-Role", auto_error=False)

VALID_ROLES = {"viewer", "analyst", "admin"}


class CurrentUser:
    def __init__(self, role: str, authenticated: bool):
        self.role = role
        self.authenticated = authenticated

    def require_role(self, *roles: str) -> None:
        if self.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"error": "forbidden", "message": f"Role '{self.role}' is not allowed for this operation."},
            )


async def get_current_user(
    api_key: Optional[str] = Security(_api_key_header),
    role_header: Optional[str] = Security(_role_header),
) -> CurrentUser:
    # If auth is disabled (empty hash), allow everything as admin
    if not settings.auth_enabled:
        return CurrentUser(role="admin", authenticated=False)

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "unauthorized", "message": "Missing X-API-Key header."},
            headers={"WWW-Authenticate": "ApiKey"},
        )

    if not settings.verify_api_key(api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "unauthorized", "message": "Invalid API key."},
            headers={"WWW-Authenticate": "ApiKey"},
        )

    role = role_header if role_header in VALID_ROLES else "viewer"
    return CurrentUser(role=role, authenticated=True)


# Convenience shortcuts
def require_analyst(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    user.require_role("analyst", "admin")
    return user


def require_admin(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    user.require_role("admin")
    return user
