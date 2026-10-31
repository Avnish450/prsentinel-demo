from typing import List, Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import AuditLog
from backend.schemas import AuditLogResponse
from backend.auth import verify_admin_password, get_current_user
from backend.config import ADMIN_TOKEN

router = APIRouter(prefix="/api", tags=["auth"])

class LoginRequest(BaseModel):
    password: str

class LoginResponse(BaseModel):
    token: str
    role: str
    user: str

@router.post("/auth/login", response_model=LoginResponse)
def login(req: LoginRequest):
    if not verify_admin_password(req.password):
        raise HTTPException(status_code=401, detail="Invalid administrator credentials")
    return LoginResponse(
        token=ADMIN_TOKEN,
        role="admin",
        user="admin"
    )

@router.get("/auth/me")
def get_me(user_info: dict = Depends(get_current_user)):
    return user_info

@router.get("/audit", response_model=List[AuditLogResponse])
def get_audit_trail(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """Retrieve chronologically ordered audit logs for policy changes, findings triage, and repo management."""
    return db.query(AuditLog).order_by(AuditLog.created_at.desc()).offset(offset).limit(limit).all()

