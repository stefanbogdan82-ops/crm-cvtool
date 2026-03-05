from fastapi import FastAPI
from app.core.logging import setup_logging
from app.api.cv import router as cv_router
from app.api.jobs import router as jobs_router
from app.db.models import Base
from app.db.session import engine

def create_app() -> FastAPI:
    setup_logging()
    app = FastAPI(title="CV Conversion Tool (MVP)")

    # MVP: auto-create tables. Replace with Alembic later.
    Base.metadata.create_all(bind=engine)

    app.include_router(cv_router)
    app.include_router(jobs_router)

    return app

app = create_app()
