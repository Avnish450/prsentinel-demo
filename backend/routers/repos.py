from typing import List, Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import Repo, ScanJob, Finding
from backend.schemas import RepoCreate, RepoResponse
from backend.services.git_service import (
    validate_github_url, InvalidRepoURLError,
    normalize_repo_input, resolve_website_github_repo, GITHUB_URL_REGEX
)
from backend.services.crypto_service import encrypt_token, sanitize_text
from backend.services.audit_service import record_audit_event, sanitize_repo_text
from backend.services.job_runner import GLOBAL_JOB_RUNNER
from backend.auth import get_current_user

router = APIRouter(prefix="/api/repos", tags=["repos"])

class ResolveRepoRequest(BaseModel):
    input: str

class ResolveRepoResponse(BaseModel):
    detected_type: str  # website_url, git_clone, git_url, github_url
    original_input: str
    resolved_url: str
    owner: str
    name: str
    message: str

@router.post("/resolve", response_model=ResolveRepoResponse)
def resolve_repo_input(req: ResolveRepoRequest):
    """
    Parses and auto-detects user input whether it is:
    - A website URL (e.g. project docs or https://github.com/owner/repo)
    - A Git clone command (e.g. git clone https://github.com/owner/repo.git)
    - A Git URL (e.g. https://github.com/owner/repo.git)
    Resolves it to a validated GitHub repository URL.
    """
    raw = (req.input or "").strip()
    if not raw:
        raise HTTPException(status_code=400, detail="Input URL or command cannot be empty")

    detected_type = "website_url"
    if raw.lower().startswith("git clone "):
        detected_type = "git_clone"
    elif raw.endswith(".git"):
        detected_type = "git_url"
    elif "github.com" in raw:
        detected_type = "github_url"

    cleaned = normalize_repo_input(raw)

    # If it is a generic website outside GitHub, attempt discovery
    if not GITHUB_URL_REGEX.match(cleaned) and (cleaned.startswith("http://") or cleaned.startswith("https://")):
        discovered = resolve_website_github_repo(cleaned)
        if discovered:
            cleaned = discovered
            message = f"Discovered GitHub repository from website: {discovered}"
        else:
            raise HTTPException(
                status_code=400,
                detail=f"No GitHub repository link discovered on website '{raw}'. Please provide the GitHub repository URL."
            )
    else:
        message = {
            "git_clone": "Parsed from Git clone command",
            "git_url": "Parsed from Git .git URL",
            "github_url": "Direct GitHub repository URL",
            "website_url": "Resolved from Website URL"
        }.get(detected_type, "Resolved successfully")

    try:
        norm_url, owner, name = validate_github_url(cleaned)
    except InvalidRepoURLError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return ResolveRepoResponse(
        detected_type=detected_type,
        original_input=raw,
        resolved_url=norm_url,
        owner=owner,
        name=name,
        message=message
    )

@router.get("", response_model=List[RepoResponse])
def list_repos(db: Session = Depends(get_db)):
    repos = db.query(Repo).order_by(Repo.created_at.desc()).all()
    res = []
    for r in repos:
        findings_count = db.query(Finding).filter(Finding.repo_id == r.id).count()
        res.append(RepoResponse(
            id=r.id,
            url=r.url,
            owner=r.owner,
            name=r.name,
            default_branch=r.default_branch,
            clone_status=r.clone_status,
            has_token=bool(r.encrypted_token),
            last_scanned_at=r.last_scanned_at,
            created_at=r.created_at,
            updated_at=r.updated_at,
            findings_count=findings_count
        ))
    return res

@router.post("", response_model=RepoResponse, status_code=status.HTTP_201_CREATED)
async def create_and_clone_repo(
    repo_in: RepoCreate,
    db: Session = Depends(get_db),
    user_info: dict = Depends(get_current_user)
):
    r"""
    Validate GitHub URL strictly against ^https://github\.com/[\w.-]+/[\w.-]+(\.git)?$
    Reject file://, ssh://, option-like strings, etc.
    Create repo record and queue clone & scan job.
    """
    raw = (repo_in.url or "").strip()
    cleaned = normalize_repo_input(raw)
    if not GITHUB_URL_REGEX.match(cleaned) and (cleaned.startswith("http://") or cleaned.startswith("https://")):
        discovered = resolve_website_github_repo(cleaned)
        if discovered:
            cleaned = discovered

    try:
        norm_url, owner, name = validate_github_url(cleaned)
    except InvalidRepoURLError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Check if already exists
    existing = db.query(Repo).filter(Repo.url == norm_url).first()
    if existing:
        repo = existing
        if repo_in.token:
            repo.encrypted_token = encrypt_token(repo_in.token)
            db.commit()
    else:
        encrypted = encrypt_token(repo_in.token) if repo_in.token else None
        repo = Repo(
            url=norm_url,
            owner=sanitize_repo_text(owner),
            name=sanitize_repo_text(name),
            default_branch="main",
            clone_status="pending",
            encrypted_token=encrypted
        )
        db.add(repo)
        db.commit()
        db.refresh(repo)

        record_audit_event(
            db,
            user=user_info.get("user", "admin"),
            action="CREATE_REPO",
            resource_type="repo",
            resource_id=repo.id,
            details={"url": norm_url, "owner": owner, "name": name}
        )

    # Queue a scan job automatically
    mode = repo_in.scan_mode or "open_prs"
    scan_job = ScanJob(
        repo_id=repo.id,
        mode=mode,
        status="queued",
        progress=0,
        current_step="Queued for scan",
        params=repo_in.params or {}
    )
    db.add(scan_job)
    db.commit()
    db.refresh(scan_job)

    # Trigger job in background runner
    await GLOBAL_JOB_RUNNER.enqueue(scan_job.id)

    findings_count = db.query(Finding).filter(Finding.repo_id == repo.id).count()
    return RepoResponse(
        id=repo.id,
        url=repo.url,
        owner=repo.owner,
        name=repo.name,
        default_branch=repo.default_branch,
        clone_status=repo.clone_status,
        has_token=bool(repo.encrypted_token),
        last_scanned_at=repo.last_scanned_at,
        created_at=repo.created_at,
        updated_at=repo.updated_at,
        findings_count=findings_count
    )

@router.get("/{repo_id}", response_model=RepoResponse)
def get_repo(repo_id: str, db: Session = Depends(get_db)):
    repo = db.query(Repo).filter(Repo.id == repo_id).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    findings_count = db.query(Finding).filter(Finding.repo_id == repo.id).count()
    return RepoResponse(
        id=repo.id,
        url=repo.url,
        owner=repo.owner,
        name=repo.name,
        default_branch=repo.default_branch,
        clone_status=repo.clone_status,
        has_token=bool(repo.encrypted_token),
        last_scanned_at=repo.last_scanned_at,
        created_at=repo.created_at,
        updated_at=repo.updated_at,
        findings_count=findings_count
    )

@router.delete("/{repo_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_repo(
    repo_id: str,
    db: Session = Depends(get_db),
    user_info: dict = Depends(get_current_user)
):
    repo = db.query(Repo).filter(Repo.id == repo_id).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    record_audit_event(
        db,
        user=user_info.get("user", "admin"),
        action="DELETE_REPO",
        resource_type="repo",
        resource_id=repo.id,
        details={"url": repo.url}
    )
    db.delete(repo)
    db.commit()

@router.post("/{repo_id}/rescan")
async def rescan_repo(
    repo_id: str,
    mode: str = Query("open_prs"),
    db: Session = Depends(get_db),
    user_info: dict = Depends(get_current_user)
):
    repo = db.query(Repo).filter(Repo.id == repo_id).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    scan_job = ScanJob(
        repo_id=repo.id,
        mode=mode,
        status="queued",
        progress=0,
        current_step="Queued for rescan"
    )
    db.add(scan_job)
    db.commit()
    db.refresh(scan_job)

    record_audit_event(
        db,
        user=user_info.get("user", "admin"),
        action="RESCAN_REPO",
        resource_type="scan_job",
        resource_id=scan_job.id,
        details={"repo_id": repo.id, "mode": mode}
    )

    await GLOBAL_JOB_RUNNER.enqueue(scan_job.id)
    return {"job_id": scan_job.id, "status": "queued"}

@router.post("/{repo_id}/pull")
async def pull_and_sync_repo(
    repo_id: str,
    db: Session = Depends(get_db),
    user_info: dict = Depends(get_current_user)
):
    repo = db.query(Repo).filter(Repo.id == repo_id).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    scan_job = ScanJob(
        repo_id=repo.id,
        mode="history_audit",
        status="queued",
        progress=0,
        current_step="Queued for latest pull & history audit",
        params={"max_commits": 50}
    )
    db.add(scan_job)
    db.commit()
    db.refresh(scan_job)

    record_audit_event(
        db,
        user=user_info.get("user", "admin"),
        action="PULL_SYNC_REPO",
        resource_type="scan_job",
        resource_id=scan_job.id,
        details={"repo_id": repo.id}
    )

    await GLOBAL_JOB_RUNNER.enqueue(scan_job.id)
    return {"job_id": scan_job.id, "status": "queued"}
