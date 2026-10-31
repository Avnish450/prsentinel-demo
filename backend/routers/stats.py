from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.database import get_db
from backend.models import Repo, ScanJob, Finding
from backend.schemas import StatsResponse

router = APIRouter(prefix="/api/stats", tags=["stats"])

@router.get("", response_model=StatsResponse)
def get_stats(db: Session = Depends(get_db)):
    """
    Returns real metrics computed strictly from active database records.
    Never invents or fabricates metrics.
    """
    total_repos = db.query(Repo).count()
    total_scans = db.query(ScanJob).filter(ScanJob.status == "done").count()

    high_findings = db.query(Finding).filter(Finding.level == "HIGH").count()
    medium_findings = db.query(Finding).filter(Finding.level == "MEDIUM").count()
    low_findings = db.query(Finding).filter(Finding.level == "LOW").count()
    total_findings = high_findings + medium_findings + low_findings

    false_positives = db.query(Finding).filter(Finding.status == "false_positive").count()
    confirmed_threats = db.query(Finding).filter(Finding.status == "confirmed_threat").count()
    open_threats = db.query(Finding).filter(Finding.status == "open", Finding.level == "HIGH").count()

    fp_rate = round((false_positives / total_findings * 100), 1) if total_findings > 0 else 0.0

    # 30-day activity trend based on actual findings/jobs
    now = datetime.now(timezone.utc)
    trend_days = 14
    trend_map = {}
    for i in range(trend_days):
        day_str = (now - timedelta(days=trend_days - 1 - i)).strftime("%b %d")
        trend_map[day_str] = {"date": day_str, "scans": 0, "findings": 0}

    # Aggregate recent jobs
    recent_jobs = db.query(ScanJob).filter(
        ScanJob.created_at >= now - timedelta(days=trend_days)
    ).all()
    for j in recent_jobs:
        day_str = j.created_at.strftime("%b %d")
        if day_str in trend_map:
            trend_map[day_str]["scans"] += 1

    # Aggregate recent findings
    recent_findings = db.query(Finding).filter(
        Finding.created_at >= now - timedelta(days=trend_days)
    ).all()
    for f in recent_findings:
        day_str = f.created_at.strftime("%b %d")
        if day_str in trend_map:
            trend_map[day_str]["findings"] += 1

    activity_trend = list(trend_map.values())

    # Needs attention queue (unresolved HIGH findings)
    urgent_findings = db.query(Finding).filter(
        Finding.level == "HIGH",
        Finding.status.in_(["open", "confirmed_threat"])
    ).order_by(Finding.score.desc()).limit(8).all()

    needs_attention = [
        {
            "id": f.id,
            "title": f.title,
            "score": f.score,
            "level": f.level,
            "status": f.status,
            "target_ref": f.target_ref,
            "file_path": f.file_path,
            "created_at": f.created_at.isoformat() if f.created_at else None
        }
        for f in urgent_findings
    ]

    return StatsResponse(
        total_repos=total_repos,
        total_scans=total_scans,
        high_findings=high_findings,
        medium_findings=medium_findings,
        low_findings=low_findings,
        false_positive_rate=fp_rate,
        threats_confirmed=confirmed_threats,
        open_threats=open_threats,
        activity_trend=activity_trend,
        needs_attention=needs_attention
    )

