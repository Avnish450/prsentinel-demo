from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import Policy
from backend.schemas import PolicyResponse, PolicyUpdate
from backend.services.audit_service import record_audit_event
from backend.auth import get_current_user

router = APIRouter(prefix="/api/policy", tags=["policy"])

def get_or_create_default_policy(db: Session) -> Policy:
    policy = db.query(Policy).filter(Policy.id == "default").first()
    if not policy:
        policy = Policy(
            id="default",
            fail_on_level="HIGH",
            fail_on_score=70,
            sensitive_keywords=[
                "raise", "valid", "sanit", "auth", "escape", "verify",
                "permission", "token", "password", "..", "startswith",
                "isinstance", "assert", "secure", "check", "allowlist", "whitelist"
            ],
            protected_paths=["auth/**", "security/**", "admin/**", "api/**"],
            trusted_authors=["dependabot[bot]", "github-actions[bot]"],
            signal_toggles={
                "fix_reversal": True,
                "sensitive_keywords": True,
                "cleanup_title": True,
                "account_age": True,
                "first_time": True
            }
        )
        db.add(policy)
        db.commit()
        db.refresh(policy)
    return policy

@router.get("", response_model=PolicyResponse)
def get_policy(db: Session = Depends(get_db)):
    return get_or_create_default_policy(db)

@router.put("", response_model=PolicyResponse)
def update_policy(
    update: PolicyUpdate,
    db: Session = Depends(get_db),
    user_info: dict = Depends(get_current_user)
):
    policy = get_or_create_default_policy(db)

    if update.fail_on_level is not None:
        policy.fail_on_level = update.fail_on_level
    if update.fail_on_score is not None:
        policy.fail_on_score = update.fail_on_score
    if update.sensitive_keywords is not None:
        policy.sensitive_keywords = update.sensitive_keywords
    if update.protected_paths is not None:
        policy.protected_paths = update.protected_paths
    if update.trusted_authors is not None:
        policy.trusted_authors = update.trusted_authors
    if update.signal_toggles is not None:
        policy.signal_toggles = update.signal_toggles

    db.commit()
    db.refresh(policy)

    record_audit_event(
        db,
        user=user_info.get("user", "admin"),
        action="UPDATE_POLICY",
        resource_type="policy",
        resource_id=policy.id,
        details={
            "fail_on_level": policy.fail_on_level,
            "fail_on_score": policy.fail_on_score
        }
    )
    return policy

