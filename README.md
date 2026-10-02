# Travel Website

Monorepo for a travel-booking platform.

## Applications

- `backend/` — FastAPI API, SQLAlchemy models, and Alembic migrations.
- `frontend/` — customer-facing Next.js application with the `/partner` portal.
- `admin/` — administration Next.js application.
- `hotel-partner/` — compatibility note; the working partner portal lives in `frontend/`.
- `docs/` — roadmap and technical design documents.

## Local setup

### Backend (Windows PowerShell)

```powershell
cd backend
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements.private-storage.txt -r requirements.public-media.txt
Copy-Item .env.example .env # skip this if .env already exists
.\venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

The API documentation is available at <http://127.0.0.1:8000/docs>.

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

### Admin

```powershell
cd admin
npm install
npm run dev -- --port 3001
```

## Antigravity editor setup

Open the repository root as the workspace. The committed workspace and Pyrefly settings point Python tooling at `backend/venv`, add `backend` to the import path, and load `backend/.env`. After first setup, reload the editor window if diagnostics still show cached missing-import errors. If an older interpreter selection still overrides the workspace default, run **Python: Select Interpreter**, choose `backend\venv\Scripts\python.exe`, and reload once.

See [the project roadmap](docs/roadmap.md) for current status and next work.
See [production deployment](docs/production-deployment.md) for the release topology and checklist.
