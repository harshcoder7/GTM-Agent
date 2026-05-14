from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session
from db.session import get_db
from db import models
from services import deep_research, composio_gmail, runtime_config
from pydantic import BaseModel

router = APIRouter(prefix="/api", tags=["dashboard"])


@router.get("/stats")
def stats(db: Session = Depends(get_db)):
    total = db.query(func.count(models.Run.id)).scalar() or 0
    drafted = db.query(func.count(models.Run.id)).filter(models.Run.status == "drafted").scalar() or 0
    escalated = db.query(func.count(models.Run.id)).filter(models.Run.status == "escalated").scalar() or 0
    rejected = db.query(func.count(models.Run.id)).filter(models.Run.status == "rejected").scalar() or 0
    awaiting = db.query(func.count(models.Run.id)).filter(models.Run.status == "awaiting_review").scalar() or 0
    avg_icp = db.query(func.avg(models.Run.icp_score)).scalar()
    return {
        "total": total, "drafted": drafted, "escalated": escalated,
        "rejected": rejected, "awaiting_review": awaiting,
        "avg_icp_score": round(float(avg_icp), 2) if avg_icp else None,
    }


@router.get("/health/deps")
async def health_deps():
    return {
        "deep_research": await deep_research.health(),
    }


