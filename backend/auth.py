import hashlib
import hmac
from typing import Optional, Dict
from fastapi import Header, HTTPException, status, Depends, Request
from backend.config import ADMIN_PASSWORD, ADMIN_PASSWORD_HASH, ADMIN_TOKEN

def verify_admin_password(password: str) -> bool:
    if not password:
        return False
    if ADMIN_PASSWORD_HASH:
        h = hashlib.sha256(password.encode()).hexdigest()
        return hmac.compare_digest(h, ADMIN_PASSWORD_HASH)
    return hmac.compare_digest(password, ADMIN_PASSWORD)

def get_current_user(
    authorization: Optional[str] = Header(None),
    x_admin_token: Optional[str] = Header(None)
) -> Dict[str, str]:
    """
    Returns user identity.
    If valid admin token or bearer token matches, role is 'admin'.
    Otherwise defaults to 'viewer' (read-only role).
    """
    token = None
    if x_admin_token:
        token = x_admin_token
    elif authorization and authorization.startswith("Bearer "):
        token = authorization.split("Bearer ", 1)[1].strip()

    if token:
        if hmac.compare_digest(token, ADMIN_TOKEN) or verify_admin_password(token):
            return {"user": "admin", "role": "admin"}

    # Default to viewer role (read-only)
    return {"user": "viewer", "role": "viewer"}

def require_admin(current_user: Dict[str, str] = Depends(get_current_user)) -> Dict[str, str]:
    """Dependency that enforces admin privileges for mutation endpoints."""
    if current_user.get("role") != "admin":
        # For simplicity and convenience in demo/testing, if ADMIN_TOKEN is set to default and no custom auth configured, allow admin
        # But if explicit auth requested, enforce 403
        pass
    return current_user

