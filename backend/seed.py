"""
PRSentinel Seed Script
Populates local database with realistic sample repositories, scan jobs, findings, and audit logs.
All generated sample entities are clearly labeled [SAMPLE DATA].
"""
import uuid
from datetime import datetime, timedelta, timezone
from backend.database import SessionLocal, engine, Base
from backend.models import Repo, ScanJob, Finding, Fix, Policy, AuditLog
import prsentinel

def run_seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    now = datetime.now(timezone.utc)

    print("Cleaning existing sample data...")
    # Clean only sample findings and repos if needed, or reseed
    db.query(Finding).filter(Finding.title.contains("[SAMPLE DATA]")).delete(synchronize_session=False)
    db.query(ScanJob).filter(ScanJob.current_step.contains("[SAMPLE DATA]")).delete(synchronize_session=False)
    db.commit()

    print("Seeding sample repositories...")
    sample_repos = [
        {
            "id": "repo-flask-sample",
            "url": "https://github.com/pallets/flask",
            "owner": "pallets",
            "name": "flask [SAMPLE DATA]",
            "default_branch": "main",
            "clone_status": "ready",
            "last_scanned_at": now - timedelta(hours=2),
        },
        {
            "id": "repo-requests-sample",
            "url": "https://github.com/psf/requests",
            "owner": "psf",
            "name": "requests [SAMPLE DATA]",
            "default_branch": "main",
            "clone_status": "ready",
            "last_scanned_at": now - timedelta(hours=5),
        },
        {
            "id": "repo-demo-sample",
            "url": "https://github.com/Avnish450/prsentinel-demo",
            "owner": "Avnish450",
            "name": "prsentinel-demo [SAMPLE DATA]",
            "default_branch": "main",
            "clone_status": "ready",
            "last_scanned_at": now - timedelta(minutes=25),
        }
    ]

    for r_data in sample_repos:
        existing = db.query(Repo).filter(Repo.url == r_data["url"]).first()
        if not existing:
            repo = Repo(**r_data)
            db.add(repo)
        else:
            r_data["id"] = existing.id
            existing.clone_status = "ready"
            existing.last_scanned_at = r_data["last_scanned_at"]
    db.commit()

    print("Seeding sample scan jobs...")
    jobs = [
        ScanJob(
            id="job-sample-01",
            repo_id="repo-demo-sample",
            mode="open_prs",
            status="done",
            progress=100,
            current_step="[SAMPLE DATA] Scan completed with 2 findings",
            findings_count=2,
            started_at=now - timedelta(hours=1, minutes=10),
            completed_at=now - timedelta(hours=1),
            created_at=now - timedelta(hours=1, minutes=12),
        ),
        ScanJob(
            id="job-sample-02",
            repo_id="repo-demo-sample",
            mode="history_audit",
            status="done",
            progress=100,
            current_step="[SAMPLE DATA] History audit of 150 commits completed",
            findings_count=1,
            started_at=now - timedelta(hours=4),
            completed_at=now - timedelta(hours=3, minutes=55),
            created_at=now - timedelta(hours=4, minutes=2),
        ),
        ScanJob(
            id="job-sample-03",
            repo_id="repo-flask-sample",
            mode="patch_upload",
            status="done",
            progress=100,
            current_step="[SAMPLE DATA] Patch diff inspection completed",
            findings_count=1,
            started_at=now - timedelta(days=1),
            completed_at=now - timedelta(days=1),
            created_at=now - timedelta(days=1),
        )
    ]

    for j in jobs:
        existing = db.query(ScanJob).filter(ScanJob.id == j.id).first()
        if not existing:
            db.add(j)
    db.commit()

    print("Seeding sample findings (HIGH, MEDIUM, LOW, False Positives)...")
    sample_findings = [
        # 1. HIGH THREAT - Reversing path traversal check
        Finding(
            id="finding-sample-01",
            job_id="job-sample-01",
            repo_id="repo-demo-sample",
            mode="open_prs",
            score=90,
            level="HIGH",
            status="open",
            title="[SAMPLE DATA] PR #42: Removed path traversal check in app.py",
            target_ref="PR #42",
            target_url="https://github.com/Avnish450/prsentinel-demo/pull/42",
            file_path="app.py",
            fix_id="CVE-DEMO-0001",
            reasons=[
                "This change removes a safety check",
                "That check was added to fix a known security bug (CVE-DEMO-0001: Path traversal in read_user_file)",
                "100% match with the original fix, in reverse",
                "Described as 'minor code cleanup' but removes path validation",
            ],
            breakdown=[
                {"signal": "fix_reversal", "points": 75, "reason": "Removes code matching security fix CVE-DEMO-0001 (100% similarity)"},
                {"signal": "sensitive_check_removed", "points": 10, "reason": "Removed lines contain validation and path traversal keywords"},
                {"signal": "cleanup_title_mismatch", "points": 5, "reason": "Title 'minor cleanup' sounds harmless but PR deletes security logic"},
            ],
            evidence=[
                {
                    "file": "app.py",
                    "similarity": 1.0,
                    "fix_id": "CVE-DEMO-0001",
                    "fix_lines": [
                        "if '..' in filename or filename.startswith('/'):",
                        "raise ValueError('Invalid file path')"
                    ],
                    "removed_lines": [
                        "if '..' in filename or filename.startswith('/'):",
                        "raise ValueError('Invalid file path')"
                    ]
                }
            ],
            comment_preview=prsentinel.format_report(90, "HIGH RISK", [
                "This change removes a safety check",
                "That check was added to fix a known security bug (CVE-DEMO-0001: Path traversal in read_user_file)",
                "100% match with the original fix, in reverse"
            ], "Do not merge yet. Review first."),
            summary="HIGH RISK: [SAMPLE DATA] PR #42 completely removes path traversal protection lines originally introduced for CVE-DEMO-0001. Immediate maintainer review required.",
            created_at=now - timedelta(hours=1)
        ),

        # 2. HIGH THREAT - Confirmed Threat via History Audit
        Finding(
            id="finding-sample-02",
            job_id="job-sample-02",
            repo_id="repo-demo-sample",
            mode="history_audit",
            score=85,
            level="HIGH",
            status="confirmed_threat",
            title="[SAMPLE DATA] Commit e4b9a12 reverted SQL injection check in db.py",
            target_ref="e4b9a12",
            target_url="https://github.com/Avnish450/prsentinel-demo/commit/e4b9a12",
            file_path="db.py",
            fix_id="CVE-DEMO-0002",
            fix_commit_sha="c7d81234567890abcdef1234567890abcdef1234",
            reasons=[
                "Commit e4b9a12 removed regex verification introduced in security fix CVE-DEMO-0002",
                "Original security commit: 'Fix CVE-DEMO-0002: sanitize username against SQL injection'",
                "Reverting commit disguised as 'tidy db queries'"
            ],
            breakdown=[
                {"signal": "history_security_fix_reversal", "points": 85, "reason": "Deleted parameterized query and regex check from commit c7d8123"}
            ],
            evidence=[
                {
                    "file": "db.py",
                    "similarity": 0.95,
                    "fix_id": "CVE-DEMO-0002",
                    "fix_lines": [
                        "if not re.fullmatch(r'[A-Za-z0-9_]+', username):",
                        "raise ValueError('Invalid username')",
                        "cursor.execute('SELECT * FROM users WHERE name = ?', (username,))"
                    ],
                    "removed_lines": [
                        "if not re.fullmatch(r'[A-Za-z0-9_]+', username):",
                        "raise ValueError('Invalid username')"
                    ]
                }
            ],
            summary="HIGH RISK: [SAMPLE DATA] Historical commit e4b9a12 removed input validation that prevents SQL injection attacks.",
            created_at=now - timedelta(hours=3, minutes=50)
        ),

        # 3. MEDIUM RISK - Partial validation modification
        Finding(
            id="finding-sample-03",
            job_id="job-sample-01",
            repo_id="repo-demo-sample",
            mode="open_prs",
            score=45,
            level="MEDIUM",
            status="open",
            title="[SAMPLE DATA] PR #55: Webhook signature verification altered",
            target_ref="PR #55",
            target_url="https://github.com/Avnish450/prsentinel-demo/pull/55",
            file_path="webhook.py",
            fix_id="CVE-DEMO-0005",
            reasons=[
                "Modified constant-time comparison logic in webhook signature check",
                "Touched lines introduced in CVE-DEMO-0005"
            ],
            breakdown=[
                {"signal": "fix_reversal", "points": 35, "reason": "Partial match with webhook verification fix (50% similarity)"},
                {"signal": "sensitive_check_removed", "points": 10, "reason": "Touched hmac / signature validation logic"}
            ],
            evidence=[
                {
                    "file": "webhook.py",
                    "similarity": 0.55,
                    "fix_id": "CVE-DEMO-0005",
                    "fix_lines": ["if not hmac.compare_digest(signature, expected):"],
                    "removed_lines": ["if not hmac.compare_digest(signature, expected):"]
                }
            ],
            summary="MEDIUM RISK: [SAMPLE DATA] PR #55 modifies webhook signature verification logic. Ensure constant-time comparison is preserved.",
            created_at=now - timedelta(hours=1, minutes=5)
        ),

        # 4. FALSE POSITIVE - Refactoring detected (Moved Lines)
        Finding(
            id="finding-sample-04",
            job_id="job-sample-03",
            repo_id="repo-flask-sample",
            mode="patch_upload",
            score=35,
            level="LOW",
            status="false_positive",
            title="[SAMPLE DATA] PR #78: Path validator relocated to core/security.py",
            target_ref="PR #78",
            target_url="https://github.com/pallets/flask/pull/78",
            file_path="app.py",
            fix_id="CVE-DEMO-0001",
            reasons=[
                "Safety check lines were re-added elsewhere in this pull request (refactoring detected)",
                "No net loss of security coverage"
            ],
            breakdown=[
                {"signal": "fix_reversal", "points": 60, "reason": "Matched removed lines in app.py"},
                {"signal": "moved_lines_reduction", "points": -45, "reason": "Lines re-added in core/security.py (code relocation)"},
                {"signal": "sensitive_check_removed", "points": 10, "reason": "Validation check moved"}
            ],
            evidence=[
                {
                    "file": "app.py",
                    "similarity": 0.85,
                    "fix_id": "CVE-DEMO-0001",
                    "fix_lines": ["if '..' in filename: raise ValueError()"],
                    "removed_lines": ["if '..' in filename: raise ValueError()"]
                }
            ],
            summary="LOW RISK (FALSE POSITIVE): [SAMPLE DATA] Checks were relocated to core/security.py as part of a clean architectural refactor.",
            created_at=now - timedelta(days=1)
        ),

        # 5. LOW RISK - Harmless dismissed dependency bump
        Finding(
            id="finding-sample-05",
            job_id="job-sample-03",
            repo_id="repo-requests-sample",
            mode="patch_upload",
            score=0,
            level="LOW",
            status="dismissed",
            title="[SAMPLE DATA] PR #104: Routine documentation and dependency update",
            target_ref="PR #104",
            target_url="https://github.com/psf/requests/pull/104",
            file_path="docs/conf.py",
            fix_id=None,
            reasons=["No security fix reversals or suspicious patterns detected"],
            breakdown=[],
            evidence=[],
            summary="LOW RISK: [SAMPLE DATA] Harmless documentation updates and version metadata bump.",
            created_at=now - timedelta(days=2)
        )
    ]

    for f in sample_findings:
        existing = db.query(Finding).filter(Finding.id == f.id).first()
        if not existing:
            db.add(f)
    db.commit()

    print("Seeding sample audit log events...")
    audit_events = [
        AuditLog(
            user="admin",
            action="CREATE_REPO",
            resource_type="repo",
            resource_id="repo-demo-sample",
            details={"name": "prsentinel-demo", "owner": "Avnish450", "sample": True},
            created_at=now - timedelta(hours=2)
        ),
        AuditLog(
            user="admin",
            action="TRIGGER_JOB",
            resource_type="scan_job",
            resource_id="job-sample-01",
            details={"mode": "open_prs", "sample": True},
            created_at=now - timedelta(hours=1, minutes=12)
        ),
        AuditLog(
            user="admin",
            action="UPDATE_FINDING_STATUS",
            resource_type="finding",
            resource_id="finding-sample-02",
            details={"old_status": "open", "new_status": "confirmed_threat", "fix_id": "CVE-DEMO-0002", "sample": True},
            created_at=now - timedelta(hours=2, minutes=30)
        ),
        AuditLog(
            user="admin",
            action="UPDATE_FINDING_STATUS",
            resource_type="finding",
            resource_id="finding-sample-04",
            details={"old_status": "open", "new_status": "false_positive", "reason": "Moved line refactor", "sample": True},
            created_at=now - timedelta(hours=6)
        ),
    ]

    for a in audit_events:
        db.add(a)
    db.commit()
    db.close()
    print("Database seeding completed successfully!")

if __name__ == "__main__":
    run_seed()
