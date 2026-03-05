import uuid
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.sql import func

class Base(DeclarativeBase):
    pass

class Candidate(Base):
    __tablename__ = "candidates"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    full_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    email: Mapped[str | None] = mapped_column(String(256), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())

class CVDocument(Base):
    __tablename__ = "cv_documents"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    candidate_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("candidates.id"), nullable=True)
    original_filename: Mapped[str] = mapped_column(String(512))
    mime_type: Mapped[str] = mapped_column(String(128))
    storage_uri: Mapped[str] = mapped_column(Text)
    sha256: Mapped[str] = mapped_column(String(64))
    uploaded_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())

class CVRevision(Base):
    __tablename__ = "cv_revisions"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    candidate_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("candidates.id"), nullable=True)
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cv_documents.id"))
    schema_version: Mapped[str] = mapped_column(String(64), default="cv-json-v1")
    parser_version: Mapped[str] = mapped_column(String(64), default="parser-v1")
    ai_prompt_version: Mapped[str] = mapped_column(String(64), default="prompt-v1")
    cv_json: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())

class RenderedCV(Base):
    __tablename__ = "rendered_cvs"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    revision_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cv_revisions.id"))
    template_version: Mapped[str] = mapped_column(String(64), default="company-v1")
    docx_uri: Mapped[str] = mapped_column(Text)
    pdf_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())

class Job(Base):
    __tablename__ = "jobs"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    type: Mapped[str] = mapped_column(String(64))  # upload_parse_render
    status: Mapped[str] = mapped_column(String(32), default="queued")  # queued|processing|done|failed
    result_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    