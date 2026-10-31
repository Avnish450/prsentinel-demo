from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import Fix
from backend.schemas import FixCreate, FixUpdate, FixResponse, FixImportRequest
from backend.services.osv_service import fetch_osv_vulnerability, extract_fix_from_osv
from backend.services.audit_service import record_audit_event
from backend.auth import get_current_user

router = APIRouter(prefix="/api/fixes", tags=["fixes"])

@router.get("", response_model=List[FixResponse])
def list_fixes(db: Session = Depends(get_db)):
    return db.query(Fix).order_by(Fix.created_at.desc()).all()

@router.post("", response_model=FixResponse, status_code=status.HTTP_201_CREATED)
def create_fix(
    fix_in: FixCreate,
    db: Session = Depends(get_db),
    user_info: dict = Depends(get_current_user)
):
    existing = db.query(Fix).filter(Fix.id == fix_in.id).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Fix '{fix_in.id}' already exists")

    fix = Fix(
        id=fix_in.id,
        description=fix_in.description,
        file=fix_in.file,
        source=fix_in.source,
        package=fix_in.package,
        severity=fix_in.severity,
        verified=fix_in.verified,
        enabled=fix_in.enabled,
        fix_added_lines=fix_in.fix_added_lines,
        commit_url=fix_in.commit_url
    )
    db.add(fix)
    db.commit()
    db.refresh(fix)

    record_audit_event(
        db,
        user=user_info.get("user", "admin"),
        action="CREATE_FIX",
        resource_type="fix",
        resource_id=fix.id,
        details={"file": fix.file, "description": fix.description}
    )
    return fix

@router.get("/{fix_id}", response_model=FixResponse)
def get_fix(fix_id: str, db: Session = Depends(get_db)):
    fix = db.query(Fix).filter(Fix.id == fix_id).first()
    if not fix:
        raise HTTPException(status_code=404, detail="Fix not found")
    return fix

@router.put("/{fix_id}", response_model=FixResponse)
def update_fix(
    fix_id: str,
    update: FixUpdate,
    db: Session = Depends(get_db),
    user_info: dict = Depends(get_current_user)
):
    fix = db.query(Fix).filter(Fix.id == fix_id).first()
    if not fix:
        raise HTTPException(status_code=404, detail="Fix not found")

    if update.description is not None:
        fix.description = update.description
    if update.file is not None:
        fix.file = update.file
    if update.package is not None:
        fix.package = update.package
    if update.severity is not None:
        fix.severity = update.severity
    if update.verified is not None:
        fix.verified = update.verified
    if update.enabled is not None:
        fix.enabled = update.enabled
    if update.fix_added_lines is not None:
        fix.fix_added_lines = update.fix_added_lines
    if update.commit_url is not None:
        fix.commit_url = update.commit_url

    db.commit()
    db.refresh(fix)

    record_audit_event(
        db,
        user=user_info.get("user", "admin"),
        action="UPDATE_FIX",
        resource_type="fix",
        resource_id=fix.id,
        details={"enabled": fix.enabled, "verified": fix.verified}
    )
    return fix

@router.delete("/{fix_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_fix(
    fix_id: str,
    db: Session = Depends(get_db),
    user_info: dict = Depends(get_current_user)
):
    fix = db.query(Fix).filter(Fix.id == fix_id).first()
    if not fix:
        raise HTTPException(status_code=404, detail="Fix not found")

    record_audit_event(
        db,
        user=user_info.get("user", "admin"),
        action="DELETE_FIX",
        resource_type="fix",
        resource_id=fix.id,
        details={"id": fix_id}
    )
    db.delete(fix)
    db.commit()

@router.post("/import", response_model=FixResponse)
def import_fix_osv(
    req: FixImportRequest,
    db: Session = Depends(get_db),
    user_info: dict = Depends(get_current_user)
):
    """
    Import fix rule from OSV API by CVE or GHSA ID, or from a GitHub commit URL.
    Returns preview or saves to fixes table.
    """
    if not req.id and not req.commit_url:
        raise HTTPException(status_code=400, detail="Must provide either an advisory ID (CVE/GHSA) or a commit URL")

    try:
        if req.id:
            vuln_data = fetch_osv_vulnerability(req.id)
            extracted = extract_fix_from_osv(vuln_data)
        else:
            # Commit URL only
            extracted = {
                "id": f"FIX-{req.commit_url.split('/')[-1][:8].upper()}",
                "description": f"Security patch from commit {req.commit_url.split('/')[-1][:8]}",
                "package": "custom",
                "file": "app.py",
                "severity": "HIGH",
                "source": "osv",
                "verified": False,
                "enabled": True,
                "fix_added_lines": [],
                "commit_url": req.commit_url
            }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to import from OSV: {str(e)}")

    if req.preview_only:
        # Return transient preview object without saving
        return FixResponse(
            id=extracted["id"],
            description=extracted["description"],
            file=extracted["file"],
            source=extracted["source"],
            package=extracted.get("package"),
            severity=extracted["severity"],
            verified=extracted["verified"],
            enabled=extracted["enabled"],
            fix_added_lines=extracted.get("fix_added_lines", []),
            commit_url=extracted.get("commit_url"),
            created_at=None,
            updated_at=None
        )

    # Persist or update fix in database
    existing = db.query(Fix).filter(Fix.id == extracted["id"]).first()
    if existing:
        existing.description = extracted["description"]
        existing.file = extracted["file"]
        existing.severity = extracted["severity"]
        existing.verified = extracted["verified"]
        existing.fix_added_lines = extracted["fix_added_lines"]
        existing.commit_url = extracted["commit_url"]
        db.commit()
        db.refresh(existing)
        return existing

    fix = Fix(
        id=extracted["id"],
        description=extracted["description"],
        file=extracted["file"],
        source=extracted["source"],
        package=extracted.get("package"),
        severity=extracted["severity"],
        verified=extracted["verified"],
        enabled=extracted["enabled"],
        fix_added_lines=extracted.get("fix_added_lines", []),
        commit_url=extracted.get("commit_url")
    )
    db.add(fix)
    db.commit()
    db.refresh(fix)

    record_audit_event(
        db,
        user=user_info.get("user", "admin"),
        action="IMPORT_FIX_OSV",
        resource_type="fix",
        resource_id=fix.id,
        details={"source": "osv", "id": fix.id}
    )
    return fix

