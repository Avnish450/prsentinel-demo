from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict

class RepoCreate(BaseModel):
    url: str
    token: Optional[str] = None
    scan_mode: Optional[str] = "open_prs"
    params: Optional[Dict[str, Any]] = None

class RepoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    url: str
    owner: str
    name: str
    default_branch: str
    clone_status: str
    has_token: bool = False
    last_scanned_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    findings_count: int = 0

class ScanJobCreate(BaseModel):
    repo_id: Optional[str] = None
    mode: str = "open_prs"  # open_prs, single_pr, history_audit, branch_compare, patch_upload
    params: Optional[Dict[str, Any]] = None
    patch_content: Optional[str] = None

class ScanJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    repo_id: Optional[str] = None
    mode: str
    status: str
    progress: int
    current_step: str
    params: Optional[Dict[str, Any]] = None
    findings_count: int = 0
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime

class FindingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    job_id: str
    repo_id: Optional[str] = None
    mode: str
    score: int
    level: str
    status: str
    title: str
    target_ref: str
    target_url: Optional[str] = None
    file_path: str
    fix_id: Optional[str] = None
    fix_commit_sha: Optional[str] = None
    reasons: List[str] = []
    breakdown: List[Dict[str, Any]] = []
    evidence: List[Dict[str, Any]] = []
    comment_preview: Optional[str] = None
    summary: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class FindingStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(open|confirmed_threat|false_positive|dismissed)$")

class FixCreate(BaseModel):
    id: str
    description: str
    file: str
    source: str = "manual"
    package: Optional[str] = None
    severity: str = "HIGH"
    verified: bool = False
    enabled: bool = True
    fix_added_lines: List[str] = []
    commit_url: Optional[str] = None

class FixUpdate(BaseModel):
    description: Optional[str] = None
    file: Optional[str] = None
    package: Optional[str] = None
    severity: Optional[str] = None
    verified: Optional[bool] = None
    enabled: Optional[bool] = None
    fix_added_lines: Optional[List[str]] = None
    commit_url: Optional[str] = None

class FixResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    description: str
    file: str
    source: str
    package: Optional[str] = None
    severity: str
    verified: bool
    enabled: bool
    fix_added_lines: List[str] = []
    commit_url: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class FixImportRequest(BaseModel):
    id: Optional[str] = None
    commit_url: Optional[str] = None
    preview_only: bool = False

class RuleTestRequest(BaseModel):
    diff: str
    title: Optional[str] = ""
    author: Optional[str] = ""
    age_days: Optional[int] = None
    first_time: Optional[bool] = False
    custom_fix: Optional[Dict[str, Any]] = None

class PolicyUpdate(BaseModel):
    fail_on_level: Optional[str] = None
    fail_on_score: Optional[int] = None
    sensitive_keywords: Optional[List[str]] = None
    protected_paths: Optional[List[str]] = None
    trusted_authors: Optional[List[str]] = None
    signal_toggles: Optional[Dict[str, bool]] = None

class PolicyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    fail_on_level: str
    fail_on_score: int
    sensitive_keywords: List[str]
    protected_paths: List[str]
    trusted_authors: List[str]
    signal_toggles: Dict[str, bool]
    updated_at: datetime

class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user: str
    action: str
    resource_type: str
    resource_id: str
    details: Dict[str, Any]
    created_at: datetime

class StatsResponse(BaseModel):
    total_repos: int
    total_scans: int
    high_findings: int
    medium_findings: int
    low_findings: int
    false_positive_rate: float
    threats_confirmed: int
    open_threats: int
    activity_trend: List[Dict[str, Any]] = []
    needs_attention: List[Dict[str, Any]] = []
