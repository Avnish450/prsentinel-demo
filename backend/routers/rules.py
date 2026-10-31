from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import Fix, Policy
from backend.schemas import RuleTestRequest
import prsentinel

router = APIRouter(prefix="/api/rules", tags=["rules"])

@router.post("/test")
def test_diff_rule(req: RuleTestRequest, db: Session = Depends(get_db)):
    """
    Simulate and test rule evaluation on a diff against active fixes or a custom fix candidate.
    Returns deterministic score, level, breakdown, evidence, and reasons.
    """
    # Fetch active fixes
    fixes_models = db.query(Fix).filter(Fix.enabled == True).all()
    fixes = [
        {
            "id": f.id,
            "description": f.description,
            "file": f.file,
            "severity": f.severity,
            "fix_added_lines": f.fix_added_lines or [],
            "enabled": True
        }
        for f in fixes_models
    ]

    # If custom fix provided, prepend it
    if req.custom_fix:
        fixes.insert(0, {
            "id": req.custom_fix.get("id", "CUSTOM-TEST-RULE"),
            "description": req.custom_fix.get("description", "Custom Test Rule"),
            "file": req.custom_fix.get("file", "app.py"),
            "severity": req.custom_fix.get("severity", "HIGH"),
            "fix_added_lines": req.custom_fix.get("fix_added_lines", []),
            "enabled": True
        })

    policy_model = db.query(Policy).filter(Policy.id == "default").first()
    policy = {
        "sensitive_keywords": policy_model.sensitive_keywords if policy_model else None,
        "signal_toggles": policy_model.signal_toggles if policy_model else {}
    }

    context = {
        "title": req.title or "",
        "author": req.author or "",
        "age_days": req.age_days,
        "first_time": req.first_time or False
    }

    result = prsentinel.analyze_diff(
        diff_text=req.diff,
        context=context,
        fixes=fixes,
        policy=policy
    )

    # Attach formatted report
    result["comment_preview"] = prsentinel.format_report(
        result["score"], result["level"], result["reasons"], result["advice"]
    )
    return result

