import hashlib
from sqlalchemy.orm import Session
from cv_tool.app.db import models

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def create_job(db: Session, job_type: str) -> models.Job:
    job = models.Job(type=job_type, status="queued")
    db.add(job); db.commit(); db.refresh(job)
    return job

def update_job(db: Session, job: models.Job, status: str, result_json=None, error: str | None = None) -> models.Job:
    job.status = status
    job.result_json = result_json
    job.error = error
    db.add(job); db.commit(); db.refresh(job)
    return job

def create_document(db: Session, original_filename: str, mime_type: str, storage_uri: str, sha256: str) -> models.CVDocument:
    doc = models.CVDocument(
        original_filename=original_filename,
        mime_type=mime_type,
        storage_uri=storage_uri,
        sha256=sha256,
    )
    db.add(doc); db.commit(); db.refresh(doc)
    return doc

def create_revision(db: Session, document_id, cv_json: dict, parser_version="parser-v1", ai_prompt_version="prompt-v1") -> models.CVRevision:
    rev = models.CVRevision(
        document_id=document_id,
        cv_json=cv_json,
        parser_version=parser_version,
        ai_prompt_version=ai_prompt_version,
    )
    db.add(rev); db.commit(); db.refresh(rev)
    return rev

def create_rendered(db: Session, revision_id, template_version: str, docx_uri: str, pdf_uri: str | None = None) -> models.RenderedCV:
    r = models.RenderedCV(
        revision_id=revision_id,
        template_version=template_version,
        docx_uri=docx_uri,
        pdf_uri=pdf_uri,
    )
    db.add(r); db.commit(); db.refresh(r)
    return r
