import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship
from backend.database import Base

def utc_now():
    return datetime.now(timezone.utc)

def gen_uuid():
    return str(uuid.uuid4())

class Repo(Base):
    __tablename__ = "repos"

    id = Column(String(64), primary_key=True, default=gen_uuid)
    url = Column(String(512), unique=True, nullable=False, index=True)
    owner = Column(String(128), nullable=False)
    name = Column(String(128), nullable=False)
    default_branch = Column(String(64), default="main")
    clone_status = Column(String(32), default="pending")  # pending, ready, cloning, failed
    encrypted_token = Column(Text, nullable=True)
    last_scanned_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    jobs = relationship("ScanJob", back_populates="repo", cascade="all, delete-orphan")
    findings = relationship("Finding", back_populates="repo", cascade="all, delete-orphan")

class ScanJob(Base):
    __tablename__ = "scan_jobs"

    id = Column(String(64), primary_key=True, default=gen_uuid)
    repo_id = Column(String(64), ForeignKey("repos.id", ondelete="CASCADE"), nullable=True, index=True)
    mode = Column(String(32), nullable=False)  # open_prs, single_pr, history_audit, branch_compare, patch_upload
    status = Column(String(32), default="queued", index=True)  # queued, cloning, indexing, scanning, done, failed, cancelled
    progress = Column(Integer, default=0)
    current_step = Column(String(256), default="Job queued")
    params = Column(JSON, default=dict)
    findings_count = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    repo = relationship("Repo", back_populates="jobs")
    findings = relationship("Finding", back_populates="job", cascade="all, delete-orphan")

class Finding(Base):
    __tablename__ = "findings"

    id = Column(String(64), primary_key=True, default=gen_uuid)
    job_id = Column(String(64), ForeignKey("scan_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    repo_id = Column(String(64), ForeignKey("repos.id", ondelete="CASCADE"), nullable=True, index=True)
    mode = Column(String(32), nullable=False)
    score = Column(Integer, nullable=False)
    level = Column(String(16), nullable=False, index=True)  # HIGH, MEDIUM, LOW
    status = Column(String(32), default="open", index=True)  # open, confirmed_threat, false_positive, dismissed
    title = Column(String(512), nullable=False)
    target_ref = Column(String(256), nullable=False)  # e.g. PR #12, commit abc1234, or patch
    target_url = Column(String(512), nullable=True)
    file_path = Column(String(512), nullable=False)
    fix_id = Column(String(128), nullable=True, index=True)
    fix_commit_sha = Column(String(64), nullable=True)
    reasons = Column(JSON, default=list)
    breakdown = Column(JSON, default=list)
    evidence = Column(JSON, default=list)
    comment_preview = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    job = relationship("ScanJob", back_populates="findings")
    repo = relationship("Repo", back_populates="findings")

class Fix(Base):
    __tablename__ = "fixes"

    id = Column(String(128), primary_key=True)  # e.g. CVE-DEMO-0001 or GHSA-xxx
    description = Column(String(512), nullable=False)
    file = Column(String(256), nullable=False)
    source = Column(String(32), default="manual")  # osv, demo, manual
    package = Column(String(128), nullable=True)
    severity = Column(String(32), default="HIGH")  # CRITICAL, HIGH, MODERATE, LOW
    verified = Column(Boolean, default=False)
    enabled = Column(Boolean, default=True)
    fix_added_lines = Column(JSON, default=list)
    commit_url = Column(String(512), nullable=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

class Policy(Base):
    __tablename__ = "policies"

    id = Column(String(64), primary_key=True, default="default")
    fail_on_level = Column(String(16), default="HIGH")  # HIGH, MEDIUM, LOW, NEVER
    fail_on_score = Column(Integer, default=70)
    sensitive_keywords = Column(JSON, default=lambda: [
        "raise", "valid", "sanit", "auth", "escape", "verify",
        "permission", "token", "password", "..", "startswith",
        "isinstance", "assert", "secure", "check", "allowlist", "whitelist"
    ])
    protected_paths = Column(JSON, default=lambda: ["auth/**", "security/**", "admin/**", "api/**"])
    trusted_authors = Column(JSON, default=lambda: ["dependabot[bot]", "github-actions[bot]"])
    signal_toggles = Column(JSON, default=lambda: {
        "fix_reversal": True,
        "sensitive_keywords": True,
        "cleanup_title": True,
        "account_age": True,
        "first_time": True
    })
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(String(64), primary_key=True, default=gen_uuid)
    user = Column(String(128), default="admin")
    action = Column(String(64), nullable=False)  # e.g. CREATE_REPO, DELETE_REPO, UPDATE_STATUS, etc.
    resource_type = Column(String(64), nullable=False)
    resource_id = Column(String(128), nullable=False)
    details = Column(JSON, default=dict)
    created_at = Column(DateTime, default=utc_now)

