from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models import Job

router = APIRouter(prefix="/v1/jobs", tags=["jobs"])

@router.get("/{job_id}")
def get_job(job_id: str, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "id": str(job.id),
        "type": job.type,
        "status": job.status,
        "result": job.result_json,
        "error": job.error,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
    }