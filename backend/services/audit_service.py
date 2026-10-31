import html
import re
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from backend.models import AuditLog

def sanitize_repo_text(text: Optional[str]) -> str:
    """
    Sanitize and escape repo-derived text (commit messages, PR titles, file paths, diff lines)
    to completely prevent XSS and control-character injection.
    """
    if text is None:
        return ""
    # Strip non-printable control characters except newline and tab
    cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", str(text))
    # Escape HTML characters: < > & " '
    return html.escape(cleaned)

def record_audit_event(
    db: Session,
    user: str,
    action: str,
    resource_type: str,
    resource_id: str,
    details: Optional[Dict[str, Any]] = None
) -> AuditLog:
    """Record an audit trail event for state modifications."""
    event = AuditLog(
        user=user or "admin",
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details or {}
    )
    db.add(event)
    db.commit()
    return event

