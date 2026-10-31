from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import ScanJob, Repo
from backend.schemas import ScanJobCreate, ScanJobResponse
from backend.services.job_runner import GLOBAL_JOB_RUNNER, LOG_MANAGER
from backend.services.audit_service import record_audit_event
from backend.auth import get_current_user

router = APIRouter(prefix="/api/jobs", tags=["jobs"])

@router.get("", response_model=List[ScanJobResponse])
def list_jobs(
    limit: int = Query(25, ge=1, le=100),
    repo_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    q = db.query(ScanJob)
    if repo_id:
        q = q.filter(ScanJob.repo_id == repo_id)
    jobs = q.order_by(ScanJob.created_at.desc()).limit(limit).all()
    return jobs

@router.post("", response_model=ScanJobResponse, status_code=status.HTTP_201_CREATED)
async def create_job(
    job_in: ScanJobCreate,
    db: Session = Depends(get_db),
    user_info: dict = Depends(get_current_user)
):
    params = job_in.params or {}
    if job_in.patch_content:
        params["patch_content"] = job_in.patch_content

    # If repo_id provided, verify repo exists
    if job_in.repo_id:
        repo = db.query(Repo).filter(Repo.id == job_in.repo_id).first()
        if not repo:
            raise HTTPException(status_code=404, detail="Repository not found")

    job = ScanJob(
        repo_id=job_in.repo_id,
        mode=job_in.mode,
        status="queued",
        progress=0,
        current_step="Scan queued",
        params=params
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    record_audit_event(
        db,
        user=user_info.get("user", "admin"),
        action="TRIGGER_JOB",
        resource_type="scan_job",
        resource_id=job.id,
        details={"mode": job.mode, "repo_id": job.repo_id}
    )

    await GLOBAL_JOB_RUNNER.enqueue(job.id)
    return job

@router.get("/{job_id}", response_model=ScanJobResponse)
def get_job(job_id: str, db: Session = Depends(get_db)):
    job = db.query(ScanJob).filter(ScanJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Scan job not found")
    return job

@router.get("/{job_id}/logs")
def get_job_logs(job_id: str, offset: int = Query(0, ge=0), db: Session = Depends(get_db)):
    job = db.query(ScanJob).filter(ScanJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Scan job not found")

    logs = LOG_MANAGER.get_logs(job_id, offset=offset)
    return {
        "job_id": job_id,
        "status": job.status,
        "progress": job.progress,
        "current_step": job.current_step,
        "offset": offset + len(logs),
        "logs": logs
    }

@router.post("/{job_id}/cancel")
def cancel_job(
    job_id: str,
    db: Session = Depends(get_db),
    user_info: dict = Depends(get_current_user)
):
    success = GLOBAL_JOB_RUNNER.cancel_job(job_id)
    if not success:
        raise HTTPException(status_code=400, detail="Job cannot be cancelled (already completed or not found)")

    record_audit_event(
        db,
        user=user_info.get("user", "admin"),
        action="CANCEL_JOB",
        resource_type="scan_job",
        resource_id=job_id,
        details={}
    )
    return {"message": "Job cancellation initiated", "job_id": job_id}

