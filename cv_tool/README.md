### Run (local)

1) Start Postgres (example via docker):
   docker run --name cvtool-postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=cvtool -p 5432:5432 -d postgres:16

2) Create .env from .env.example and set DATABASE_URL.

3) Install deps:
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   pip install -e .

4) Run API:
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

5) Upload:
   curl -F "file=@/path/to/CV.docx" http://localhost:8000/v1/cv/upload