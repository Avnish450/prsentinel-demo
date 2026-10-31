import asyncio
import traceback
from datetime import datetime, timezone
from typing import Dict, List, Set, Optional
from sqlalchemy.orm import Session
from backend.config import MAX_CONCURRENT_JOBS
from backend.database import SessionLocal
from backend.models import ScanJob, Repo, Finding, Fix, Policy, AuditLog
from backend.services.crypto_service import decrypt_token, sanitize_text
from backend.services.git_service import safe_clone_repo, GitServiceError
from backend.services.scanner_service import (
    run_patch_scan, run_single_pr_scan, run_open_prs_scan,
    run_history_audit, run_branch_compare
)

class JobLogManager:
    """Stores in-memory live logs for active & recent jobs."""
    def __init__(self):
        self._logs: Dict[str, List[Dict[str, str]]] = {}

    def add_log(self, job_id: str, message: str, level: str = "info"):
        sanitized = sanitize_text(message)
        ts = datetime.now(timezone.utc).strftime("%H:%M:%S.%f")[:-3]
        entry = {"timestamp": ts, "message": sanitized, "level": level}
        if job_id not in self._logs:
            self._logs[job_id] = []
        self._logs[job_id].append(entry)

    def get_logs(self, job_id: str, offset: int = 0) -> List[Dict[str, str]]:
        entries = self._logs.get(job_id, [])
        return entries[offset:]

LOG_MANAGER = JobLogManager()

class JobRunner:
    def __init__(self):
        self.queue: asyncio.Queue = asyncio.Queue()
        self.semaphore = asyncio.Semaphore(MAX_CONCURRENT_JOBS)
        self.cancelled_jobs: Set[str] = set()
        self.worker_tasks: List[asyncio.Task] = []
        self._running = False

    def start(self):
        if not self._running:
            self._running = True
            for i in range(MAX_CONCURRENT_JOBS):
                task = asyncio.create_task(self._worker_loop(i))
                self.worker_tasks.append(task)

    def stop(self):
        self._running = False
        for task in self.worker_tasks:
            task.cancel()
        self.worker_tasks.clear()

    async def enqueue(self, job_id: str):
        LOG_MANAGER.add_log(job_id, f"Scan job {job_id[:8]} added to execution queue.")
        await self.queue.put(job_id)

    def cancel_job(self, job_id: str) -> bool:
        db = SessionLocal()
        try:
            job = db.query(ScanJob).filter(ScanJob.id == job_id).first()
            if not job or job.status in ("done", "failed", "cancelled"):
                return False
            self.cancelled_jobs.add(job_id)
            job.status = "cancelled"
            job.current_step = "Job cancelled by user"
            job.completed_at = datetime.now(timezone.utc)
            db.commit()
            LOG_MANAGER.add_log(job_id, "Cancellation requested by user. Terminating job...", level="warn")
            return True
        finally:
            db.close()

    async def _worker_loop(self, worker_id: int):
        while self._running:
            try:
                job_id = await self.queue.get()
                if job_id in self.cancelled_jobs:
                    self.queue.task_done()
                    continue

                async with self.semaphore:
                    await self._process_job(job_id)
                self.queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[Worker-{worker_id}] Unhandled error: {e}")

    def _is_cancelled(self, job_id: str) -> bool:
        return job_id in self.cancelled_jobs

    async def _process_job(self, job_id: str):
        db: Session = SessionLocal()
        try:
            job = db.query(ScanJob).filter(ScanJob.id == job_id).first()
            if not job:
                return

            if self._is_cancelled(job_id):
                job.status = "cancelled"
                job.completed_at = datetime.now(timezone.utc)
                db.commit()
                return

            job.status = "cloning" if job.mode != "patch_upload" else "scanning"
            job.started_at = datetime.now(timezone.utc)
            job.progress = 10
            job.current_step = "Initializing scanner environment"
            db.commit()

            repo = db.query(Repo).filter(Repo.id == job.repo_id).first() if job.repo_id else None
            token = decrypt_token(repo.encrypted_token) if repo and repo.encrypted_token else None

            # Load active fixes & policy
            fixes_models = db.query(Fix).filter(Fix.enabled == True).all()
            fixes = [
                {
                    "id": f.id,
                    "description": f.description,
                    "file": f.file,
                    "severity": f.severity,
                    "source": f.source,
                    "fix_added_lines": f.fix_added_lines or [],
                    "enabled": f.enabled
                }
                for f in fixes_models
            ]

            policy_model = db.query(Policy).filter(Policy.id == "default").first()
            policy = {
                "fail_on_level": policy_model.fail_on_level if policy_model else "HIGH",
                "fail_on_score": policy_model.fail_on_score if policy_model else 70,
                "sensitive_keywords": policy_model.sensitive_keywords if policy_model else None,
                "protected_paths": policy_model.protected_paths if policy_model else None,
                "trusted_authors": policy_model.trusted_authors if policy_model else None,
                "signal_toggles": policy_model.signal_toggles if policy_model else {}
            }

            def logger_fn(msg: str):
                LOG_MANAGER.add_log(job_id, msg)

            findings_to_insert = []

            # Execute based on scan mode
            if job.mode == "patch_upload":
                job.status = "scanning"
                job.progress = 40
                job.current_step = "Scanning uploaded patch diff"
                db.commit()

                patch_content = (job.params or {}).get("patch_content", "")
                title = (job.params or {}).get("title", "Uploaded Patch")
                res = run_patch_scan(patch_content, title=title, fixes=fixes, policy=policy, logger=logger_fn)

                if res["score"] >= 40:
                    findings_to_insert.append({
                        "mode": "patch_upload",
                        "score": res["score"],
                        "level": res["level"],
                        "title": title,
                        "target_ref": "Uploaded Patch",
                        "target_url": None,
                        "file_path": res["evidence"][0]["file"] if res["evidence"] else "unknown",
                        "fix_id": res["evidence"][0].get("fix_id") if res["evidence"] else None,
                        "fix_commit_sha": None,
                        "reasons": res["reasons"],
                        "breakdown": res["breakdown"],
                        "evidence": res["evidence"],
                        "comment_preview": prsentinel.format_report(res["score"], res["level"], res["reasons"], res["advice"]),
                        "summary": res["summary"]
                    })

            elif job.mode == "single_pr":
                job.status = "scanning"
                job.progress = 35
                job.current_step = "Fetching PR diff and metadata"
                db.commit()

                pr_url = (job.params or {}).get("pr_url") or (repo.url + "/pull/1" if repo else "")
                res, meta = run_single_pr_scan(pr_url, token=token, fixes=fixes, policy=policy, logger=logger_fn)

                if res["score"] >= 40:
                    findings_to_insert.append({
                        "mode": "single_pr",
                        "score": res["score"],
                        "level": res["level"],
                        "title": f"PR #{meta['pr_num']}: {meta['title']}",
                        "target_ref": f"PR #{meta['pr_num']}",
                        "target_url": pr_url,
                        "file_path": res["evidence"][0]["file"] if res["evidence"] else "unknown",
                        "fix_id": res["evidence"][0].get("fix_id") if res["evidence"] else None,
                        "fix_commit_sha": None,
                        "reasons": res["reasons"],
                        "breakdown": res["breakdown"],
                        "evidence": res["evidence"],
                        "comment_preview": prsentinel.format_report(res["score"], res["level"], res["reasons"], res["advice"]),
                        "summary": res["summary"]
                    })

            elif job.mode == "open_prs":
                if not repo:
                    raise ValueError("Repository record is required for open_prs mode")

                job.status = "scanning"
                job.progress = 30
                job.current_step = "Listing and analyzing open PRs"
                db.commit()

                open_prs_findings = run_open_prs_scan(
                    repo.owner, repo.name, token=token, fixes=fixes, policy=policy, logger=logger_fn
                )

                for item in open_prs_findings:
                    res = item["scan_result"]
                    findings_to_insert.append({
                        "mode": "open_prs",
                        "score": res["score"],
                        "level": res["level"],
                        "title": item["title"],
                        "target_ref": item["target_ref"],
                        "target_url": item["target_url"],
                        "file_path": item["file_path"],
                        "fix_id": res["evidence"][0].get("fix_id") if res["evidence"] else None,
                        "fix_commit_sha": None,
                        "reasons": res["reasons"],
                        "breakdown": res["breakdown"],
                        "evidence": res["evidence"],
                        "comment_preview": prsentinel.format_report(res["score"], res["level"], res["reasons"], res["advice"]),
                        "summary": res["summary"]
                    })

            elif job.mode in ("history_audit", "branch_compare"):
                if not repo:
                    raise ValueError(f"Repository record is required for {job.mode} mode")

                job.status = "cloning"
                job.progress = 20
                job.current_step = "Securely cloning repository"
                db.commit()

                with safe_clone_repo(repo.url, token=token, logger=logger_fn) as repo_dir:
                    if self._is_cancelled(job_id):
                        raise asyncio.CancelledError()

                    job.status = "indexing"
                    job.progress = 50
                    job.current_step = "Indexing git commit graph"
                    db.commit()

                    if job.mode == "history_audit":
                        job.status = "scanning"
                        job.progress = 65
                        job.current_step = "Tracing deleted lines with git blame against security fixes"
                        db.commit()

                        max_commits = int((job.params or {}).get("max_commits", 500))
                        hist_findings = run_history_audit(repo_dir, max_commits=max_commits, fixes=fixes, logger=logger_fn)

                        for hf in hist_findings:
                            findings_to_insert.append(hf)

                    elif job.mode == "branch_compare":
                        job.status = "scanning"
                        job.progress = 60
                        job.current_step = "Diffing target branches"
                        db.commit()

                        base_b = (job.params or {}).get("base_branch", repo.default_branch or "main")
                        head_b = (job.params or {}).get("head_branch", "HEAD")
                        res = run_branch_compare(repo_dir, base_b, head_b, fixes=fixes, policy=policy, logger=logger_fn)

                        if res["score"] >= 40:
                            findings_to_insert.append({
                                "mode": "branch_compare",
                                "score": res["score"],
                                "level": res["level"],
                                "title": f"Branch Diff: {base_b}..{head_b}",
                                "target_ref": f"{base_b}..{head_b}",
                                "target_url": None,
                                "file_path": res["evidence"][0]["file"] if res["evidence"] else "unknown",
                                "fix_id": res["evidence"][0].get("fix_id") if res["evidence"] else None,
                                "fix_commit_sha": None,
                                "reasons": res["reasons"],
                                "breakdown": res["breakdown"],
                                "evidence": res["evidence"],
                                "comment_preview": prsentinel.format_report(res["score"], res["level"], res["reasons"], res["advice"]),
                                "summary": res["summary"]
                            })

            # Check cancellation before persisting
            if self._is_cancelled(job_id):
                job.status = "cancelled"
                job.current_step = "Job cancelled by user"
                job.completed_at = datetime.now(timezone.utc)
                db.commit()
                return

            # Insert findings
            for f_dict in findings_to_insert:
                finding = Finding(
                    job_id=job.id,
                    repo_id=job.repo_id,
                    mode=f_dict["mode"],
                    score=f_dict["score"],
                    level=f_dict["level"],
                    status="open",
                    title=f_dict["title"],
                    target_ref=f_dict["target_ref"],
                    target_url=f_dict.get("target_url"),
                    file_path=f_dict["file_path"],
                    fix_id=f_dict.get("fix_id"),
                    fix_commit_sha=f_dict.get("fix_commit_sha"),
                    reasons=f_dict.get("reasons", []),
                    breakdown=f_dict.get("breakdown", []),
                    evidence=f_dict.get("evidence", []),
                    comment_preview=f_dict.get("comment_preview"),
                    summary=f_dict.get("summary")
                )
                db.add(finding)

            job.findings_count = len(findings_to_insert)
            job.status = "done"
            job.progress = 100
            job.current_step = f"Scan completed successfully ({len(findings_to_insert)} finding(s) discovered)"
            job.completed_at = datetime.now(timezone.utc)

            if repo:
                repo.clone_status = "ready"
                repo.last_scanned_at = datetime.now(timezone.utc)

            db.commit()
            LOG_MANAGER.add_log(job_id, f"Scan job completed with {len(findings_to_insert)} finding(s).")

        except asyncio.CancelledError:
            db.rollback()
            job = db.query(ScanJob).filter(ScanJob.id == job_id).first()
            if job:
                job.status = "cancelled"
                job.current_step = "Job cancelled by user"
                job.completed_at = datetime.now(timezone.utc)
                db.commit()
            LOG_MANAGER.add_log(job_id, "Job execution cancelled.", level="warn")

        except Exception as e:
            db.rollback()
            err_msg = sanitize_text(str(e))
            job = db.query(ScanJob).filter(ScanJob.id == job_id).first()
            if job:
                job.status = "failed"
                job.error_message = err_msg
                job.current_step = f"Failed: {err_msg}"
                job.completed_at = datetime.now(timezone.utc)
                db.commit()
            if repo:
                repo.clone_status = "failed"
                db.commit()
            LOG_MANAGER.add_log(job_id, f"Job failed: {err_msg}", level="error")

        finally:
            db.close()

GLOBAL_JOB_RUNNER = JobRunner()

