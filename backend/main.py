import json
import os
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.config import CORS_ORIGINS, BASE_DIR
from backend.database import engine, Base, SessionLocal
from backend.models import Fix, Policy
from backend.services.job_runner import GLOBAL_JOB_RUNNER
from backend.routers import repos, jobs, findings, fixes, rules, policy, stats, auth

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Create database tables
    Base.metadata.create_all(bind=engine)

    # 2. Seed initial fixes from fixes.json if database is empty
    db = SessionLocal()
    try:
        count = db.query(Fix).count()
        if count == 0:
            fixes_file = BASE_DIR / "fixes.json"
            if fixes_file.exists():
                with open(fixes_file, "r") as f:
                    seed_fixes = json.load(f)
                    for item in seed_fixes:
                        fix_obj = Fix(
                            id=item["id"],
                            description=item["description"],
                            file=item["file"],
                            source=item.get("source", "demo"),
                            package=item.get("package", "core"),
                            severity=item.get("severity", "HIGH"),
                            verified=True,
                            enabled=True,
                            fix_added_lines=item.get("fix_added_lines", [])
                        )
                        db.add(fix_obj)
                    db.commit()

        # Seed default policy if missing
        default_pol = db.query(Policy).filter(Policy.id == "default").first()
        if not default_pol:
            pol = Policy(
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
            db.add(pol)
            db.commit()
    finally:
        db.close()

    # 3. Start job runner background workers
    GLOBAL_JOB_RUNNER.start()

    yield

    # Shutdown job runner workers
    GLOBAL_JOB_RUNNER.stop()

app = FastAPI(
    title="PRSentinel Engine & Dashboard API",
    description="Deterministic detection of pull requests reversing past security fixes",
    version="2.0.0",
    lifespan=lifespan
)

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routers
app.include_router(repos.router)
app.include_router(jobs.router)
app.include_router(findings.router)
app.include_router(fixes.router)
app.include_router(rules.router)
app.include_router(policy.router)
app.include_router(stats.router)
app.include_router(auth.router)

@app.get("/health", tags=["system"])
def health_check():
    """Health check endpoint required by deployment runners."""
    return {
        "status": "healthy",
        "service": "PRSentinel Engine",
        "version": "2.0.0",
        "runner_active": GLOBAL_JOB_RUNNER._running
    }

# Frontend static distribution integration
frontend_dist = BASE_DIR / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_frontend_spa(full_path: str):
        file_path = frontend_dist / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(frontend_dist / "index.html")

