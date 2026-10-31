from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_
from backend.database import get_db
from backend.models import Finding
from backend.schemas import FindingResponse, FindingStatusUpdate
from backend.services.audit_service import record_audit_event
from backend.auth import get_current_user

router = APIRouter(prefix="/api/findings", tags=["findings"])

@router.get("", response_model=List[FindingResponse])
def list_findings(
    level: Optional[str] = Query(None, description="HIGH, MEDIUM, or LOW"),
    status: Optional[str] = Query(None, description="open, confirmed_threat, false_positive, dismissed"),
    repo_id: Optional[str] = None,
    mode: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    q = db.query(Finding)

    if level:
        q = q.filter(Finding.level == level.upper())
    if status:
        q = q.filter(Finding.status == status.lower())
    if repo_id:
        q = q.filter(Finding.repo_id == repo_id)
    if mode:
        q = q.filter(Finding.mode == mode)
    if search:
        pattern = f"%{search}%"
        q = q.filter(
            or_(
                Finding.title.ilike(pattern),
                Finding.file_path.ilike(pattern),
                Finding.fix_id.ilike(pattern),
                Finding.target_ref.ilike(pattern)
            )
        )

    findings = q.order_by(Finding.created_at.desc()).offset(offset).limit(limit).all()
    return findings

@router.get("/{finding_id}", response_model=FindingResponse)
def get_finding(finding_id: str, db: Session = Depends(get_db)):
    finding = db.query(Finding).filter(Finding.id == finding_id).first()
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")
    return finding

@router.patch("/{finding_id}", response_model=FindingResponse)
def update_finding_status(
    finding_id: str,
    update: FindingStatusUpdate,
    db: Session = Depends(get_db),
    user_info: dict = Depends(get_current_user)
):
    finding = db.query(Finding).filter(Finding.id == finding_id).first()
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")

    old_status = finding.status
    finding.status = update.status
    db.commit()
    db.refresh(finding)

    record_audit_event(
        db,
        user=user_info.get("user", "admin"),
        action="UPDATE_FINDING_STATUS",
        resource_type="finding",
        resource_id=finding.id,
        details={
            "old_status": old_status,
            "new_status": update.status,
            "fix_id": finding.fix_id,
            "target_ref": finding.target_ref
        }
    )

    return finding

