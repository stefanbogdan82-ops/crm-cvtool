from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db import repo
from app.services.storage import storage
from app.services.extract.docx_extractor import extract_text_from_docx
from app.services.extract.pdf_extractor import extract_text_from_pdf, looks_like_scanned_pdf
from app.services.ai.client import get_ai_client
from app.services.render.docx_renderer import render_company_docx

router = APIRouter(prefix="/v1/cv", tags=["cv"])

SUPPORTED = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    # DOC legacy intentionally not supported in MVP
}

@router.post("/upload")
async def upload_cv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if file.content_type not in SUPPORTED:
        raise HTTPException(status_code=400, detail=f"Unsupported type: {file.content_type}")

    job = repo.create_job(db, "upload_parse_render")
    repo.update_job(db, job, "processing")

    try:
        raw = await file.read()
        sha = repo.sha256_bytes(raw)
        saved_path = storage.save_bytes(raw, "originals", file.filename)

        doc = repo.create_document(
            db,
            original_filename=file.filename,
            mime_type=file.content_type,
            storage_uri=saved_path,
            sha256=sha,
        )

        # Extract
        if file.content_type == "application/pdf":
            text = extract_text_from_pdf(saved_path)
            if looks_like_scanned_pdf(text):
                raise HTTPException(status_code=400, detail="PDF appears to be scanned. OCR not enabled in MVP.")
        else:
            text = extract_text_from_docx(saved_path)

        if not text.strip():
            raise HTTPException(status_code=400, detail="Could not extract text from CV.")

        # AI enrich/normalize
        ai = get_ai_client()
        ai_out = ai.enrich(text)
        cv_json = ai_out["cv_json"]

        # Save revision
        rev = repo.create_revision(db, document_id=doc.id, cv_json=cv_json)

        # Render
        rendered_bytes = render_company_docx(cv_json, template_version="company-v1")
        rendered_path = storage.save_bytes(rendered_bytes, "rendered", f"{file.filename}.company-v1.docx")

        rend = repo.create_rendered(db, revision_id=rev.id, template_version="company-v1", docx_uri=rendered_path)

        result = {
            "revision_id": str(rev.id),
            "rendered_docx_path": rendered_path,
            "open_questions": ai_out.get("open_questions", []),
            "risk_flags": ai_out.get("risk_flags", []),
        }
        repo.update_job(db, job, "done", result_json=result)
        return {"job_id": str(job.id), **result}

    except HTTPException as e:
        repo.update_job(db, job, "failed", error=str(e.detail))
        raise
    except Exception as e:
        repo.update_job(db, job, "failed", error=str(e))
        raise HTTPException(status_code=500, detail="Internal error")
    