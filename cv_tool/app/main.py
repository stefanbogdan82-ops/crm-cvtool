from fastapi import FastAPI
from cv_tool.app.core.logging import setup_logging
from cv_tool.app.api.cv import router as cv_router
from cv_tool.app.api.jobs import router as jobs_router
from cv_tool.app.db.models import Base
from cv_tool.app.db.session import engine


def create_app() -> FastAPI:
    setup_logging()

    app = FastAPI(
        title="CV Conversion Tool (MVP)",
        version="0.1.0"
    )

    # MVP: auto-create tables. Replace with Alembic later.
    Base.metadata.create_all(bind=engine)

    # Health endpoint
    @app.get("/health", tags=["system"])
    def health():
        return {"status": "ok"}

    # Routers
    app.include_router(cv_router, prefix="/api/cv", tags=["cv"])
    app.include_router(jobs_router, prefix="/api/jobs", tags=["jobs"])

    return app


app = create_app()