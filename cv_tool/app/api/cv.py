from pathlib import Path

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from fastapi import HTTPException
from openai import RateLimitError
from sqlalchemy.orm import Session

from cv_tool.app.db.session import get_db
from cv_tool.app.db import repo
from cv_tool.app.services.storage import storage
from cv_tool.app.services.extract.docx_extractor import extract_text_from_docx
from cv_tool.app.services.extract.pdf_extractor import extract_text_from_pdf, looks_like_scanned_pdf
from cv_tool.app.services.ai.client import get_ai_client
from cv_tool.app.services.ai.prompts import PROMPT_VERSION
from cv_tool.app.services.render.docx_renderer import render_company_docx

router = APIRouter(prefix="/v1/cv", tags=["cv"])

SUPPORTED_MIME = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
}

SUPPORTED_EXT = {
    ".pdf": "pdf",
    ".docx": "docx",
    ".doc": "doc",
}


def _detect_file_kind(file: UploadFile) -> str | None:
    """
    Detect file type using MIME first, then filename extension fallback.
    This is important because curl / PowerShell often sends DOCX as application/octet-stream.
    """
    content_type = (file.content_type or "").lower()
    ext = Path(file.filename or "").suffix.lower()

    if content_type in SUPPORTED_MIME:
        return SUPPORTED_MIME[content_type]

    if ext in SUPPORTED_EXT:
        return SUPPORTED_EXT[ext]

    return None

@router.get("/revisions/{revision_id}")
def get_revision(revision_id: str, db: Session = Depends(get_db)):
    from cv_tool.app.db.models import CVRevision

    rev = db.get(CVRevision, revision_id)
    if not rev:
        raise HTTPException(status_code=404, detail="Revision not found")

    return {
        "id": str(rev.id),
        "schema_version": rev.schema_version,
        "parser_version": rev.parser_version,
        "ai_prompt_version": rev.ai_prompt_version,
        "cv_json": rev.cv_json,
        "created_at": rev.created_at,
    }


@router.post("/upload")
async def upload_cv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    job = repo.create_job(db, "upload_parse_render")
    repo.update_job(db, job, "processing")

    try:
        file_kind = _detect_file_kind(file)
        if file_kind is None:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Unsupported type: content_type={file.content_type}, "
                    f"filename={file.filename}"
                ),
            )

        raw = await file.read()
        if not raw:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")

        sha = repo.sha256_bytes(raw)
        saved_path = storage.save_bytes(
            raw,
            subdir="originals",
            filename=file.filename or "uploaded_cv.docx",
            suffix="source",
        )

        doc = repo.create_document(
            db,
            original_filename=file.filename or "uploaded_cv",
            mime_type=file.content_type or "application/octet-stream",
            storage_uri=saved_path,
            sha256=sha,
        )

        # Extract text based on detected file kind
        if file_kind == "pdf":
            text = extract_text_from_pdf(saved_path)
            if looks_like_scanned_pdf(text):
                raise HTTPException(
                    status_code=400,
                    detail="PDF appears to be scanned. OCR not enabled in MVP.",
                )

        elif file_kind == "docx":
            text = extract_text_from_docx(saved_path)

        elif file_kind == "doc":
            raise HTTPException(
                status_code=400,
                detail="DOC conversion not enabled in MVP yet. Please upload DOCX or text-based PDF.",
            )

        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file kind: {file_kind}",
            )

        if not text.strip():
            raise HTTPException(
                status_code=400,
                detail="Could not extract text from CV.",
            )

        # AI enrich / normalize
        ai = get_ai_client()

        try:
            ai_out = ai.enrich(text)
        except RateLimitError as exc:
            raise HTTPException(
                status_code=503,
                detail="OpenAI quota unavailable. Check API billing, credits, and project limits."
             ) from exc
        except ValueError as exc:
            raise HTTPException(
                status_code=422,
                detail=f"AI output could not be normalized: {str(exc)}"
            ) from exc
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=f"Unexpected AI processing error: {str(exc)}"
            ) from exc

        cv_json = ai_out["cv_json"]

        try:
            rendered_bytes = render_company_docx(
                cv_json,
                template_version="company-v1",
            )
        except FileNotFoundError as exc:
            raise HTTPException(
                status_code=500,
                detail=f"DOCX template not found: {str(exc)}"
            ) from exc
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=f"DOCX rendering failed: {str(exc)}"
            ) from exc

        # Save revision
        rev = repo.create_revision(
            db,
            document_id=doc.id,
            cv_json=cv_json,
            ai_prompt_version=PROMPT_VERSION,
        )

        rendered_path = storage.save_bytes(
            rendered_bytes,
            subdir="rendered",
            filename=file.filename or "cv.docx",
         suffix="company-v1",
        )

        repo.create_rendered(
            db,
            revision_id=rev.id,
            template_version="company-v1",
            docx_uri=rendered_path,
        )

        result = {
            "revision_id": str(rev.id),
            "rendered_docx_path": rendered_path,
            "open_questions": ai_out.get("open_questions", []),
            "risk_flags": ai_out.get("risk_flags", []),
            "detected_file_kind": file_kind,
            "detected_content_type": file.content_type,
            "original_filename": file.filename,
        }

        repo.update_job(db, job, "done", result_json=result)
        return {"job_id": str(job.id), **result}

    except HTTPException as e:
        repo.update_job(db, job, "failed", error=str(e.detail))
        raise
    except Exception as e:
        repo.update_job(db, job, "failed", error=str(e))
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Internal error")
    