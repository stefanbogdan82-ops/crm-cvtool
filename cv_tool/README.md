### Run (local)

1) Start Postgres (example via docker):
   docker run --name cvtool-postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=cvtool -p 5432:5432 -d postgres:16

2) Create .env from .env.example and set DATABASE_URL.

3) Install deps:
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   pip install -e .

4) Run API:
   uvicorn cv_tool.app.main:app --reload      

5) Upload:
   curl -F "file=@/path/to/CV.docx" http://localhost:8000/v1/cv/upload

5) Upload:
   curl.exe -F "file=@C:/Proiecte/crm-cvtool/cv_tool/app/test/CV_AB.docx;type=application/vnd.openxmlformats-officedocument.wordprocessingml.document" http://localhost:8000/api/cv/v1/cv/upload

   curl.exe -F "file=@C:/path/to/file.pdf;type=application/pdf" http://localhost:8000/api/cv/v1/cv/upload

6) Activate Environment:
   from C:\Proiecte\crm-cvtool
   python -m venv .venv
   .venv\Scripts\Activate.ps1
      if not working: Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   Ctrl + shift + P -> Select Interpreter C:\Proiecte\crm-cvtool\.venv\Scripts\python.exe
   Ctrl + Shift + P -> Reload Window